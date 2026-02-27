"""Analytics event logging to Firestore."""

import logging
from datetime import datetime, timezone
from typing import Optional

from src.utils.firebase_admin import get_firestore_client

logger = logging.getLogger(__name__)


def log_query(
    user_id: Optional[str],
    session_id: Optional[str],
    question: str,
    latency_ms: int,
    chunks_used: int,
    sources_count: int,
    figures_count: int,
) -> None:
    """Log a query event to Firestore analytics/queries collection (best-effort)."""
    try:
        db = get_firestore_client()
        db.collection("analytics").document("queries").collection("events").add(
            {
                "userId": user_id or "anonymous",
                "sessionId": session_id or "",
                "questionPreview": question[:80],
                "latencyMs": latency_ms,
                "chunksUsed": chunks_used,
                "sourcesCount": sources_count,
                "figuresCount": figures_count,
                "isAnonymous": user_id is None,
                "timestamp": datetime.now(timezone.utc),
            }
        )
    except Exception as e:
        logger.warning(f"Failed to log query analytics: {e}")


def log_daily_metrics(latency_ms: int, is_error: bool = False) -> None:
    """Increment daily system metrics (best-effort)."""
    try:
        from google.cloud.firestore import Increment

        db = get_firestore_client()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        doc_ref = (
            db.collection("system")
            .document("daily")
            .collection("metrics")
            .document(today)
        )
        update = {
            "totalQueries": Increment(1),
            "totalLatencyMs": Increment(latency_ms),
        }
        if is_error:
            update["errorCount"] = Increment(1)
        doc_ref.set(update, merge=True)
    except Exception as e:
        logger.warning(f"Failed to update daily metrics: {e}")
