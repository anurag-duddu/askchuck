"""
FastAPI server for AskChuck RAG system.
Exposes RAG chain via HTTP API with streaming support.
"""

import asyncio
import json
import logging
import time
from typing import AsyncGenerator, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from groq import Groq
from sse_starlette.sse import EventSourceResponse

from src.api.auth import get_current_user
from src.api.models import HealthResponse, QueryRequest, QueryResponse
from src.generation.rag_chain import GENERATION_FAILED_MESSAGE, AskChuckRAG
from src.utils.analytics import log_daily_metrics, log_query, upsert_user_stats
from src.utils.config import configured_groq_chat_models, settings
from src.utils.groq_models import GroqModelCheck, check_groq_models

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AskChuck API",
    description="RAG API for Charles Owen's Structured Planning methodology",
    version="1.0.0",
)

# Add CORS middleware
_origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG chain (singleton)
rag_chain: AskChuckRAG | None = None


def get_rag_chain() -> AskChuckRAG:
    """Get or create the global RAG chain instance."""
    global rag_chain
    if rag_chain is None:
        logger.info("Initializing AskChuck RAG chain...")
        rag_chain = AskChuckRAG()
    return rag_chain


# Result of the startup Groq model check; /health reads it so it never calls Groq
groq_model_check: GroqModelCheck | None = None

# Hard cap on the startup model lookup: it is advisory and must not delay startup
GROQ_MODEL_CHECK_TIMEOUT_SECONDS = 5.0


async def _run_groq_model_check() -> None:
    """Warn at startup about configured Groq models that Groq no longer lists."""
    global groq_model_check
    try:
        client = Groq(
            api_key=settings.groq_api_key,
            timeout=GROQ_MODEL_CHECK_TIMEOUT_SECONDS,
            max_retries=0,
        )
        # The SDK timeout bounds each socket wait; wait_for bounds the whole check
        groq_model_check = await asyncio.wait_for(
            asyncio.to_thread(
                check_groq_models,
                client,
                configured_groq_chat_models(),
                settings.groq_vision_model,
            ),
            timeout=GROQ_MODEL_CHECK_TIMEOUT_SECONDS,
        )
    except Exception as e:  # includes asyncio.TimeoutError
        logger.warning(f"Groq model check skipped ({type(e).__name__}): {e}")


@app.on_event("startup")
async def startup_event():
    """Initialize RAG chain on startup and check the configured Groq models."""
    try:
        get_rag_chain()
        logger.info("✓ AskChuck RAG chain initialized")
    except Exception as e:
        logger.error(f"✗ Failed to initialize RAG chain: {e}")
    await _run_groq_model_check()


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns the status of the API and RAG chain availability. Status is
    "degraded" when the RAG chain is missing or the startup check found that
    Groq no longer lists any configured chat model (cached, no Groq call here).
    """
    try:
        rag_available = rag_chain is not None
        models_available = not (
            groq_model_check and groq_model_check.no_chat_model_available
        )
        return HealthResponse(
            status="healthy" if rag_available and models_available else "degraded",
            version="1.0.0",
            rag_available=rag_available,
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            version="1.0.0",
            rag_available=False,
        )


@app.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    current_user: Optional[dict] = Depends(get_current_user),
):
    """
    Non-streaming query endpoint.

    Processes a question and returns the complete response with sources and figures.
    """
    start_time = time.time()
    try:
        logger.info(f"Processing query: {request.question[:100]}...")

        # Get RAG chain
        rag = get_rag_chain()

        # Process query
        result = rag.query(
            question=request.question,
            conversation_history=request.conversation_history,
            include_figures=request.include_figures,
            top_k=request.top_k,
        )

        # Fire analytics (best-effort, non-blocking)
        latency_ms = int((time.time() - start_time) * 1000)
        asyncio.create_task(
            asyncio.to_thread(
                log_query,
                current_user["uid"] if current_user else None,
                request.session_id,
                request.question,
                latency_ms,
                result.get("chunks_used", 0),
                len(result.get("sources", [])),
                len(result.get("figures", [])),
            )
        )
        asyncio.create_task(asyncio.to_thread(log_daily_metrics, latency_ms))
        if current_user:
            asyncio.create_task(
                asyncio.to_thread(upsert_user_stats, current_user["uid"])
            )

        return QueryResponse(**result)

    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stream_query")
async def stream_query(
    request: QueryRequest,
    current_user: Optional[dict] = Depends(get_current_user),
):
    """
    Streaming query endpoint using Server-Sent Events (SSE).

    Streams tokens in real-time as they're generated, followed by metadata.
    """
    try:
        logger.info(f"Processing streaming query: {request.question[:100]}...")

        # Get RAG chain
        rag = get_rag_chain()

        start_time = time.time()

        async def event_generator() -> AsyncGenerator[dict, None]:
            """Generate SSE events from RAG chain stream."""
            chunks_used = 0
            sources_count = 0
            figures_count = 0

            try:
                # Stream from RAG chain
                for chunk in rag.stream_query(
                    question=request.question,
                    conversation_history=request.conversation_history,
                    include_figures=request.include_figures,
                    top_k=request.top_k,
                ):
                    # Capture metadata counts from stream events
                    chunk_type = chunk.get("type", "")
                    if chunk_type == "sources":
                        sources_count = len(chunk.get("sources", []))
                    elif chunk_type == "chunk_ids":
                        chunks_used = len(chunk.get("chunk_ids", []))
                    elif chunk_type == "figures":
                        figures_count = len(chunk.get("figures", []))

                    # Yield SSE event
                    yield {
                        "event": chunk_type or "message",
                        "data": json.dumps(chunk),
                    }

                    # After the "done" event, fire analytics asynchronously
                    if chunk_type == "done":
                        latency_ms = int((time.time() - start_time) * 1000)
                        asyncio.create_task(
                            asyncio.to_thread(
                                log_query,
                                current_user["uid"] if current_user else None,
                                request.session_id,
                                request.question,
                                latency_ms,
                                chunks_used,
                                sources_count,
                                figures_count,
                            )
                        )
                        asyncio.create_task(
                            asyncio.to_thread(log_daily_metrics, latency_ms)
                        )
                        if current_user:
                            asyncio.create_task(
                                asyncio.to_thread(
                                    upsert_user_stats, current_user["uid"]
                                )
                            )

            except Exception as e:
                # The detail stays in the logs; visitors get text that is safe to show
                logger.error(f"Streaming error: {e}", exc_info=True)
                yield {
                    "event": "error",
                    "data": json.dumps(
                        {"type": "error", "error": GENERATION_FAILED_MESSAGE}
                    ),
                }

        return EventSourceResponse(event_generator())

    except Exception as e:
        logger.error(f"Stream query setup failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "AskChuck API",
        "version": "1.0.0",
        "description": "RAG API for Charles Owen's Structured Planning methodology",
        "endpoints": {
            "/health": "Health check",
            "/query": "Non-streaming query (POST)",
            "/stream_query": "Streaming query with SSE (POST)",
            "/docs": "OpenAPI documentation",
        },
    }
