"""
Regression tests for Groq model selection and fallback in AskChuckRAG.

Groq periodically retires model IDs (404 model_not_found). These tests pin the
behaviour that keeps generation alive when that happens, using a scripted fake
client so no network access or real model is needed.
"""

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

import httpx  # noqa: E402
import pytest  # noqa: E402
from groq import APIConnectionError  # noqa: E402

from src.generation import rag_chain as rag_chain_module  # noqa: E402
from src.generation.rag_chain import AskChuckRAG  # noqa: E402
from src.utils.config import groq_chat_kwargs, settings  # noqa: E402

NOT_FOUND = Exception(
    "Error code: 404 - {'error': {'message': 'The model `gone` does not exist "
    "or you do not have access to it.', 'code': 'model_not_found'}}"
)
RATE_LIMITED = Exception("Error code: 429 - rate limit reached")
BAD_KEY = Exception("Error code: 401 - Invalid API Key")


class StatusError(Exception):
    """Mimics groq.APIStatusError, which carries the HTTP status as an attribute."""

    def __init__(self, status_code):
        super().__init__(f"Error code: {status_code}")
        self.status_code = status_code


def _completion(content, finish_reason="stop"):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
                finish_reason=finish_reason,
            )
        ]
    )


def _stream(*tokens):
    return iter(
        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=t))])
        for t in tokens
    )


class FakeGroq:
    """Scripted client: `script` maps model -> Exception to raise or value to return."""

    def __init__(self, script):
        self.script = script
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.script[kwargs["model"]]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    @property
    def models_called(self):
        return [c["model"] for c in self.calls]


@pytest.fixture
def rag(monkeypatch):
    monkeypatch.setattr(settings, "groq_model", "primary")
    monkeypatch.setattr(settings, "groq_fallback_models", "backup1, backup2")
    # A truthy stand-in keeps AskChuckRAG from building the real retrieval pipeline
    return AskChuckRAG(retrieval_pipeline=SimpleNamespace())


def test_model_defaults_to_settings(rag):
    assert rag.model == "primary"
    assert rag._models_to_try() == ["primary", "backup1", "backup2"]


def test_explicit_model_overrides_settings():
    chain = AskChuckRAG(retrieval_pipeline=SimpleNamespace(), model="custom")
    assert chain.model == "custom"


def test_fallbacks_are_deduplicated(rag, monkeypatch):
    monkeypatch.setattr(settings, "groq_fallback_models", "primary,backup1,backup1")
    assert rag._models_to_try() == ["primary", "backup1"]


def test_generate_falls_back_when_model_is_retired(rag):
    rag.client = FakeGroq({"primary": NOT_FOUND, "backup1": _completion("hello")})
    assert rag._generate("sys", "user") == "hello"
    assert rag.client.models_called == ["primary", "backup1"]


def test_generate_falls_back_on_rate_limit(rag):
    rag.client = FakeGroq({"primary": RATE_LIMITED, "backup1": _completion("hello")})
    assert rag._generate("sys", "user") == "hello"


def test_generate_skips_model_that_returns_empty_content(rag):
    # Reasoning models can spend the whole token budget thinking and return ""
    rag.client = FakeGroq(
        {"primary": _completion("", "length"), "backup1": _completion("hello")}
    )
    assert rag._generate("sys", "user") == "hello"
    assert rag.client.models_called == ["primary", "backup1"]


def test_generate_does_not_fall_back_on_auth_error(rag):
    rag.client = FakeGroq({"primary": BAD_KEY})
    answer = rag._generate("sys", "user")
    assert rag.client.models_called == ["primary"]
    assert answer.startswith("I encountered an error")


def test_generate_reports_error_when_every_model_fails(rag):
    rag.client = FakeGroq(
        {"primary": NOT_FOUND, "backup1": NOT_FOUND, "backup2": NOT_FOUND}
    )
    assert rag._generate("sys", "user").startswith("I encountered an error")
    assert rag.client.models_called == ["primary", "backup1", "backup2"]


def test_stream_query_falls_back_when_model_is_retired(rag, monkeypatch):
    monkeypatch.setattr(
        rag_chain_module, "build_full_prompt", lambda **_: ("sys", "user")
    )
    rag.retrieval = SimpleNamespace(retrieve=lambda **_: [{"chunk_id": "c1"}])
    rag._build_sources_list = lambda chunks: []
    rag._extract_display_figures = lambda chunks: []
    rag.client = FakeGroq({"primary": NOT_FOUND, "backup1": _stream("Hel", "lo")})

    events = list(rag.stream_query("what is an abstraction ladder?"))

    text = "".join(e["content"] for e in events if e["type"] == "token")
    assert text == "Hello"
    assert events[-1] == {"type": "done"}
    assert rag.client.models_called == ["primary", "backup1"]


def _prepare_stream(rag, monkeypatch, script):
    monkeypatch.setattr(
        rag_chain_module, "build_full_prompt", lambda **_: ("sys", "user")
    )
    rag.retrieval = SimpleNamespace(retrieve=lambda **_: [{"chunk_id": "c1"}])
    rag._build_sources_list = lambda chunks: []
    rag._extract_display_figures = lambda chunks: []
    rag.client = FakeGroq(script)


def test_stream_query_errors_instead_of_faking_an_answer_when_all_rate_limited(
    rag, monkeypatch
):
    _prepare_stream(
        rag,
        monkeypatch,
        {"primary": RATE_LIMITED, "backup1": StatusError(429), "backup2": RATE_LIMITED},
    )

    events = list(rag.stream_query("q"))

    # One terminal error event: no answer text, sources or "done" that the UI
    # could mistake for a real answer (and charge the visitor a question for)
    assert events == [{"type": "error", "error": rag_chain_module.RATE_LIMITED_MESSAGE}]
    assert rag.client.models_called == ["primary", "backup1", "backup2"]


def test_stream_query_does_not_say_busy_when_models_are_gone(rag, monkeypatch):
    # Waiting a minute won't bring back a retired model
    _prepare_stream(
        rag,
        monkeypatch,
        {"primary": NOT_FOUND, "backup1": RATE_LIMITED, "backup2": NOT_FOUND},
    )

    events = list(rag.stream_query("q"))

    assert events == [
        {"type": "error", "error": rag_chain_module.GENERATION_FAILED_MESSAGE}
    ]


def test_stream_query_hides_provider_details_on_auth_error(rag, monkeypatch):
    _prepare_stream(rag, monkeypatch, {"primary": BAD_KEY})

    events = list(rag.stream_query("q"))

    assert events == [
        {"type": "error", "error": rag_chain_module.GENERATION_FAILED_MESSAGE}
    ]
    assert "401" not in events[0]["error"]
    assert rag.client.models_called == ["primary"]  # another model can't fix a bad key


def test_stream_query_errors_when_every_model_streams_nothing(rag, monkeypatch):
    _prepare_stream(
        rag,
        monkeypatch,
        {"primary": _stream(), "backup1": _stream(), "backup2": _stream()},
    )

    events = list(rag.stream_query("q"))

    assert events == [
        {"type": "error", "error": rag_chain_module.GENERATION_FAILED_MESSAGE}
    ]


def test_stream_query_success_has_no_error_event(rag, monkeypatch):
    _prepare_stream(
        rag, monkeypatch, {"primary": RATE_LIMITED, "backup1": _stream("ok")}
    )

    events = list(rag.stream_query("q"))

    assert all(e["type"] != "error" for e in events)
    assert events[-1] == {"type": "done"}


@pytest.mark.parametrize(
    "error, expected",
    [
        (StatusError(429), True),
        (RATE_LIMITED, True),
        (StatusError(404), False),
        (NOT_FOUND, False),
        (BAD_KEY, False),
    ],
)
def test_is_rate_limit(error, expected):
    assert AskChuckRAG._is_rate_limit(error) is expected


def test_clean_model_output_rewrites_native_citations(rag):
    raw = "Design Factors record insight 【1†L1-L9】 and speculation 【2】."
    assert rag._clean_model_output(raw) == (
        "Design Factors record insight [1] and speculation [2]."
    )


def _filter_stream(tokens):
    f = rag_chain_module._CitationStreamFilter()
    return "".join(f.feed(t) for t in tokens) + f.flush()


def test_citation_filter_handles_citation_split_across_tokens():
    tokens = ["Insight 【1†L", "1-L9】 and more 【", "2", "】 end"]
    assert _filter_stream(tokens) == "Insight [1] and more [2] end"


def test_citation_filter_passes_plain_text_through_untouched():
    f = rag_chain_module._CitationStreamFilter()
    assert f.feed("No citations, only [1] plain ones.") == (
        "No citations, only [1] plain ones."
    )


def test_citation_filter_does_not_stall_on_unterminated_bracket():
    stray = "【" + "x" * 60
    # Past MAX_PENDING the filter stops holding the text back
    assert _filter_stream([stray]) == stray
    # A short unterminated tail is held until flush() so nothing is lost
    assert _filter_stream(["end 【1†L"]) == "end 【1†L"


def test_stream_query_normalizes_native_citations(rag, monkeypatch):
    monkeypatch.setattr(
        rag_chain_module, "build_full_prompt", lambda **_: ("sys", "user")
    )
    rag.retrieval = SimpleNamespace(retrieve=lambda **_: [{"chunk_id": "c1"}])
    rag._build_sources_list = lambda chunks: []
    rag._extract_display_figures = lambda chunks: []
    rag.client = FakeGroq(
        {"primary": _stream("A fact 【1†L", "1-L9】.", " Another 【2】")}
    )

    events = list(rag.stream_query("q"))

    text = "".join(e["content"] for e in events if e["type"] == "token")
    assert text == "A fact [1]. Another [2]"


def test_clean_model_output_rewrites_figure_references(rag):
    # gpt-oss puts a narrow no-break space (U+202F) inside these
    raw = "As shown in 【Figure 3】 and 【Table 2】 here 【】."
    assert rag._clean_model_output(raw) == "As shown in [Figure 3] and [Table 2] here ."


def test_citation_filter_rewrites_figure_reference_split_across_tokens():
    assert _filter_stream(["see 【Fig", "ure 3】 now"]) == "see [Figure 3] now"


@pytest.mark.parametrize("status", [404, 408, 429, 500, 502, 503, 504])
def test_falls_back_on_retryable_status_codes(rag, status):
    rag.client = FakeGroq(
        {"primary": StatusError(status), "backup1": _completion("ok")}
    )
    assert rag._generate("sys", "user") == "ok"
    assert rag.client.models_called == ["primary", "backup1"]


@pytest.mark.parametrize("status", [400, 401, 403])
def test_does_not_fall_back_on_client_errors(rag, status):
    rag.client = FakeGroq({"primary": StatusError(status)})
    rag._generate("sys", "user")
    assert rag.client.models_called == ["primary"]


def test_falls_back_on_connection_error(rag):
    connection_error = APIConnectionError(request=httpx.Request("POST", "https://x"))
    rag.client = FakeGroq({"primary": connection_error, "backup1": _completion("ok")})
    assert rag._generate("sys", "user") == "ok"


def test_groq_client_does_not_sleep_and_retry_rate_limits(rag):
    # Otherwise the SDK waits 7-15s retrying the same rate-limited model before
    # our fallback chain ever sees the 429
    assert rag.client.max_retries == 0


def test_reasoning_effort_only_for_gpt_oss():
    assert groq_chat_kwargs("openai/gpt-oss-120b") == {"reasoning_effort": "low"}
    assert groq_chat_kwargs("openai/gpt-oss-20b") == {"reasoning_effort": "low"}
    assert groq_chat_kwargs("qwen/qwen3.8-27b") == {}
