"""
Tests for the error contract of POST /stream_query.

The frontend treats an SSE `error` event as a failed question: it shows the
event's text to the visitor as-is and gives their free question back. So every
failure must arrive as an `error` event whose text is safe to show, never as
answer tokens and never with raw exception text.
"""

import json
import os
from types import SimpleNamespace

# Settings() requires these at import time; real values come from .env locally.
for _var in (
    "GROQ_API_KEY",
    "VOYAGE_API_KEY",
    "PINECONE_API_KEY",
    "PINECONE_ENVIRONMENT",
    "COHERE_API_KEY",
):
    os.environ.setdefault(_var, "test")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from src.api import server  # noqa: E402
from src.generation.rag_chain import (  # noqa: E402
    GENERATION_FAILED_MESSAGE,
    RATE_LIMITED_MESSAGE,
)


def _sse_events(body: str):
    """Parse an SSE body into [(event_name, data_dict), ...]."""
    events = []
    for block in body.replace("\r\n", "\n").strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.split("\n") if ": " in line)
        events.append((fields["event"], json.loads(fields["data"])))
    return events


@pytest.fixture
def post_stream_query(monkeypatch):
    """POST a question with `stream_query` replaced by the given generator function."""

    def post(stream_query):
        monkeypatch.setattr(
            server, "get_rag_chain", lambda: SimpleNamespace(stream_query=stream_query)
        )
        # No `with`: skips startup, which would build the real RAG chain
        response = TestClient(server.app).post(
            "/stream_query", json={"question": "what is a design factor?"}
        )
        assert response.status_code == 200
        return _sse_events(response.text)

    return post


def test_rag_error_event_reaches_the_client(post_stream_query):
    def stream_query(**_):
        yield {"type": "error", "error": RATE_LIMITED_MESSAGE}

    assert post_stream_query(stream_query) == [
        ("error", {"type": "error", "error": RATE_LIMITED_MESSAGE})
    ]


def test_unexpected_failure_becomes_a_friendly_error_event(post_stream_query):
    def stream_query(**_):
        raise RuntimeError("pinecone exploded: index host 10.0.0.7 unreachable")
        yield  # makes this a generator, like the real one

    events = post_stream_query(stream_query)

    assert events == [("error", {"type": "error", "error": GENERATION_FAILED_MESSAGE})]
    assert "pinecone" not in json.dumps(events)


def test_failure_after_partial_answer_still_ends_with_an_error_event(
    post_stream_query,
):
    def stream_query(**_):
        yield {"type": "token", "content": "Design Factors are"}
        raise ConnectionError("upstream reset")

    events = post_stream_query(stream_query)

    assert events[0] == ("token", {"type": "token", "content": "Design Factors are"})
    assert events[-1] == (
        "error",
        {"type": "error", "error": GENERATION_FAILED_MESSAGE},
    )
