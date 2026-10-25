"""
Early warning for Groq model retirements.

Groq retires model IDs from time to time, and a retired ID answers 404
model_not_found. The fallback chain in AskChuckRAG hides that only while at least
one configured model still exists, and nothing else says the list is shrinking.
check_groq_models() compares the configured IDs with Groq's live model list
(GET /openai/v1/models) at API startup and logs what is missing, so a retirement
shows up in the deploy logs before visitors hit it.

The check is advisory: it never raises, and a failed lookup only logs a warning.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence

logger = logging.getLogger(__name__)

# Listed by Groq but unable to answer a RAG question: speech-to-text, text-to-speech,
# safety classifiers and a small Arabic-focused model.
NON_ANSWERING_MODEL_PREFIXES = (
    "whisper",
    "canopylabs/orpheus",
    "meta-llama/llama-prompt-guard",
    "openai/gpt-oss-safeguard",
    "allam-",
)

# A RAG prompt is several thousand tokens and we ask for up to 2048 back, so tiny
# context windows cannot serve answers whatever they are called.
MIN_ANSWER_CONTEXT_WINDOW = 16_384

MAX_SUGGESTIONS = 10


@dataclass
class GroqModelCheck:
    """Outcome of one startup check; `checked` is False when the lookup failed."""

    checked: bool = False
    chat_models: List[str] = field(default_factory=list)
    missing_chat_models: List[str] = field(default_factory=list)
    vision_model_missing: bool = False
    # Chat-capable models Groq lists now; only filled when no chat model is left
    suggestions: List[str] = field(default_factory=list)

    @property
    def no_chat_model_available(self) -> bool:
        """True only when the lookup worked and every configured chat model is gone."""
        return (
            self.checked
            and bool(self.chat_models)
            and len(self.missing_chat_models) == len(self.chat_models)
        )


def _is_answer_capable(model: Any) -> bool:
    """Whether a listed model can plausibly answer questions (vs. speech, guard, tiny)."""
    if model.id.lower().startswith(NON_ANSWERING_MODEL_PREFIXES):
        return False
    outputs = getattr(model, "output_modalities", None)
    if outputs and "text" not in outputs:
        return False
    context_window = getattr(model, "context_window", None)
    if isinstance(context_window, int) and context_window < MIN_ANSWER_CONTEXT_WINDOW:
        return False
    return True


def _suggest_replacements(listed: Sequence[Any]) -> List[str]:
    """Answer-capable listed models, largest context window first."""
    candidates = [m for m in listed if _is_answer_capable(m)]
    candidates.sort(key=lambda m: (-(getattr(m, "context_window", None) or 0), m.id))
    return [
        (
            f"{m.id} ({m.context_window} ctx)"
            if getattr(m, "context_window", None)
            else m.id
        )
        for m in candidates[:MAX_SUGGESTIONS]
    ]


def check_groq_models(
    client: Any,
    chat_models: Sequence[str],
    vision_model: Optional[str] = None,
) -> GroqModelCheck:
    """
    Compare the configured Groq models with the ones Groq currently lists.

    Logs one WARNING per missing model, plus an ERROR naming chat-capable
    replacements when no configured chat model is left. Never raises: if the
    lookup (or anything else here) fails, it logs a WARNING and returns an
    unchecked result so startup is unaffected.
    """
    try:
        return _check(client, list(chat_models), vision_model)
    except Exception as e:
        logger.warning(
            "Groq model check skipped, could not read Groq's model list "
            "(%s: %s). Configured models were NOT verified.",
            type(e).__name__,
            str(e)[:200],
        )
        return GroqModelCheck()


def _check(
    client: Any, chat_models: List[str], vision_model: Optional[str]
) -> GroqModelCheck:
    listed = [
        m for m in client.models.list().data if getattr(m, "active", True) is not False
    ]
    available = {m.id for m in listed}

    result = GroqModelCheck(
        checked=True,
        chat_models=chat_models,
        missing_chat_models=[m for m in chat_models if m not in available],
        vision_model_missing=bool(vision_model) and vision_model not in available,
    )

    for model in result.missing_chat_models:
        logger.warning(
            "Groq model check: configured chat model '%s' is not in Groq's model "
            "list (retired or renamed). Update GROQ_MODEL / GROQ_FALLBACK_MODELS.",
            model,
        )
    if result.vision_model_missing:
        logger.warning(
            "Groq model check: configured vision model '%s' is not in Groq's model "
            "list. Chat answers are unaffected; figure description during "
            "ingestion will fail until groq_vision_model / GROQ_VISION_MODEL is "
            "updated.",
            vision_model,
        )

    if result.no_chat_model_available:
        result.suggestions = _suggest_replacements(listed)
        logger.error(
            "Groq model check: NO configured chat model is available (tried %s). "
            "Every answer will fail until GROQ_MODEL / GROQ_FALLBACK_MODELS point "
            "at models Groq still lists. Chat-capable models available now: %s.",
            ", ".join(chat_models),
            ", ".join(result.suggestions) or "none found in Groq's list",
        )
    elif not result.missing_chat_models:
        logger.info(
            "Groq model check: all %d configured chat models are available (%s)",
            len(chat_models),
            ", ".join(chat_models),
        )
    return result
