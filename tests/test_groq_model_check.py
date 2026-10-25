"""
Tests for the startup check that warns when Groq retires a configured model.

A fake client stands in for Groq's GET /openai/v1/models, so no network access or
real key is needed. The catalogue below mirrors a real response: ids and context
windows are what the check keys off, plus the non-chat models it must not suggest.
"""

import asyncio
import logging
import os
import time
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

from src.api import server  # noqa: E402
from src.utils.config import configured_groq_chat_models, settings  # noqa: E402
from src.utils.groq_models import GroqModelCheck, check_groq_models  # noqa: E402

CHAT = ["primary", "backup1", "backup2"]
VISION = "vision"


def _model(model_id, context_window=131072, **extra):
    return SimpleNamespace(id=model_id, context_window=context_window, **extra)


def _catalogue(*ids):
    return [_model(i) for i in ids]


# Models Groq lists that can never answer a RAG question
NON_CHAT = [
    _model("whisper-large-v3", 448),
    _model("whisper-large-v3-turbo", 448),
    _model("canopylabs/orpheus-v1-english", 4000),
    _model("meta-llama/llama-prompt-guard-2-86m", 512),
    _model("openai/gpt-oss-safeguard-20b", 131072),
    _model("allam-2-7b", 4096),
]


class FakeGroqModels:
    """Stands in for Groq(): `.models.list()` returns the scripted list or raises."""

    def __init__(self, models=None, error=None, delay=0.0):
        self._models, self._error, self._delay = models or [], error, delay
        self.list_calls = 0
        self.models = SimpleNamespace(list=self._list)

    def _list(self):
        self.list_calls += 1
        time.sleep(self._delay)
        if self._error:
            raise self._error
        return SimpleNamespace(data=self._models)


def _problems(caplog):
    return [r for r in caplog.records if r.levelno >= logging.WARNING]


def _check(models, caplog, chat=CHAT, vision=VISION):
    caplog.set_level(logging.INFO)
    return check_groq_models(FakeGroqModels(models), chat, vision)


def test_all_models_present_is_silent(caplog):
    result = _check(_catalogue(*CHAT, VISION), caplog)

    assert _problems(caplog) == []
    assert result.checked
    assert result.missing_chat_models == []
    assert not result.vision_model_missing
    assert not result.no_chat_model_available


def test_missing_fallback_warns_and_names_it(caplog):
    result = _check(_catalogue("primary", "backup2", VISION), caplog)

    (record,) = _problems(caplog)
    assert record.levelno == logging.WARNING
    assert "backup1" in record.getMessage()
    assert "GROQ_FALLBACK_MODELS" in record.getMessage()
    assert result.missing_chat_models == ["backup1"]
    # Answers still work through the remaining models
    assert not result.no_chat_model_available


def test_all_chat_models_missing_logs_error_with_suggestions(caplog):
    live = [
        _model("openai/gpt-oss-120b", 131072),
        _model("qwen/qwen3.8-27b", 131072),
        _model("small/chat-model", 32768),
        *NON_CHAT,
    ]
    result = _check(live, caplog)

    warnings = [
        r.getMessage() for r in _problems(caplog) if r.levelno == logging.WARNING
    ]
    (error,) = [r for r in _problems(caplog) if r.levelno == logging.ERROR]
    for model in CHAT:
        assert any(f"'{model}'" in w for w in warnings)
    assert result.no_chat_model_available

    # Suggestions come from the list response, largest context window first
    assert result.suggestions == [
        "openai/gpt-oss-120b (131072 ctx)",
        "qwen/qwen3.8-27b (131072 ctx)",
        "small/chat-model (32768 ctx)",
    ]
    message = error.getMessage()
    for suggestion in result.suggestions:
        assert suggestion in message
    # ...and never include models that cannot answer questions
    for excluded in ("whisper", "orpheus", "prompt-guard", "safeguard", "allam"):
        assert excluded not in message


def test_models_call_raising_never_crashes_startup(caplog):
    caplog.set_level(logging.INFO)
    client = FakeGroqModels(error=RuntimeError("boom: connection reset"))

    result = check_groq_models(client, CHAT, VISION)

    assert result == GroqModelCheck()
    assert not result.checked
    # Unknown is not "degraded": a failed lookup must not look like a retirement
    assert not result.no_chat_model_available
    (record,) = _problems(caplog)
    assert record.levelno == logging.WARNING
    assert "boom: connection reset" in record.getMessage()


def test_malformed_models_response_never_crashes_startup(caplog):
    caplog.set_level(logging.INFO)
    client = SimpleNamespace(models=SimpleNamespace(list=lambda: SimpleNamespace()))

    assert not check_groq_models(client, CHAT, VISION).checked
    assert [r.levelno for r in _problems(caplog)] == [logging.WARNING]


def test_missing_vision_model_warns_without_error(caplog):
    result = _check(_catalogue(*CHAT), caplog)

    (record,) = _problems(caplog)
    assert record.levelno == logging.WARNING
    assert f"'{VISION}'" in record.getMessage()
    assert "ingestion" in record.getMessage()
    assert result.vision_model_missing
    assert not result.no_chat_model_available


def test_inactive_models_count_as_missing(caplog):
    live = [_model("primary", active=False), *_catalogue("backup1", "backup2", VISION)]
    result = _check(live, caplog)

    assert result.missing_chat_models == ["primary"]


def test_suggestions_skip_non_text_output_models(caplog):
    live = [
        _model("openai/gpt-oss-120b", output_modalities=["text"]),
        _model("new-vendor/tts", output_modalities=["speech"]),
    ]
    result = _check(live, caplog)

    assert result.suggestions == ["openai/gpt-oss-120b (131072 ctx)"]


# ---- server wiring: startup never blocks or crashes, /health reads the cache ----


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setattr(settings, "groq_model", "primary")
    monkeypatch.setattr(settings, "groq_fallback_models", "backup1, backup2")
    monkeypatch.setattr(settings, "groq_vision_model", VISION)
    # Avoid building the real retrieval pipeline; the check is independent of it
    monkeypatch.setattr(server, "get_rag_chain", lambda: None)
    monkeypatch.setattr(server, "rag_chain", SimpleNamespace())
    monkeypatch.setattr(server, "groq_model_check", None)
    return monkeypatch


def _use_client(monkeypatch, client):
    monkeypatch.setattr(server, "Groq", lambda **_: client)


def test_configured_chat_models_are_primary_then_deduplicated_fallbacks(api):
    assert configured_groq_chat_models() == ["primary", "backup1", "backup2"]
    api.setattr(settings, "groq_fallback_models", "primary,backup1,backup1")
    assert configured_groq_chat_models() == ["primary", "backup1"]


def test_startup_survives_models_call_raising(api, caplog):
    caplog.set_level(logging.INFO)
    _use_client(api, FakeGroqModels(error=RuntimeError("boom")))

    asyncio.run(server.startup_event())  # must not raise

    assert server.groq_model_check == GroqModelCheck()
    assert asyncio.run(server.health_check()).status == "healthy"


def test_startup_survives_client_construction_failing(api):
    def explode(**_):
        raise RuntimeError("bad client config")

    api.setattr(server, "Groq", explode)

    asyncio.run(server.startup_event())  # must not raise

    assert server.groq_model_check is None


def test_startup_does_not_wait_for_a_slow_models_call(api, caplog):
    caplog.set_level(logging.INFO)
    api.setattr(server, "GROQ_MODEL_CHECK_TIMEOUT_SECONDS", 0.05)
    _use_client(api, FakeGroqModels(_catalogue(*CHAT), delay=0.5))

    started = time.monotonic()

    async def start():
        await server.startup_event()
        return time.monotonic() - started

    # Measured inside the loop: asyncio.run itself then waits out the worker thread
    assert asyncio.run(start()) < 0.4
    assert server.groq_model_check is None
    assert any(r.levelno == logging.WARNING for r in caplog.records)


def test_health_is_degraded_when_no_chat_model_is_available(api):
    _use_client(api, FakeGroqModels(_catalogue("something-else")))
    asyncio.run(server.startup_event())

    response = asyncio.run(server.health_check())

    assert response.status == "degraded"
    assert response.rag_available


def test_health_stays_healthy_when_only_a_fallback_is_missing(api):
    _use_client(api, FakeGroqModels(_catalogue("primary", "backup2", VISION)))
    asyncio.run(server.startup_event())

    assert asyncio.run(server.health_check()).status == "healthy"


def test_health_never_calls_groq(api):
    client = FakeGroqModels(_catalogue(*CHAT, VISION))
    _use_client(api, client)
    asyncio.run(server.startup_event())
    assert client.list_calls == 1

    for _ in range(3):
        asyncio.run(server.health_check())

    assert client.list_calls == 1
