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
from sse_starlette.sse import EventSourceResponse

from src.api.auth import get_current_user
from src.api.models import HealthResponse, QueryRequest, QueryResponse
from src.generation.rag_chain import AskChuckRAG
from src.utils.analytics import log_daily_metrics, log_query, upsert_user_stats

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify frontend domain
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


@app.on_event("startup")
async def startup_event():
    """Initialize RAG chain on startup."""
    try:
        get_rag_chain()
        logger.info("✓ AskChuck RAG chain initialized")
    except Exception as e:
        logger.error(f"✗ Failed to initialize RAG chain: {e}")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns the status of the API and RAG chain availability.
    """
    try:
        rag_available = rag_chain is not None
        return HealthResponse(
            status="healthy" if rag_available else "degraded",
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
                logger.error(f"Streaming error: {e}", exc_info=True)
                yield {
                    "event": "error",
                    "data": json.dumps({"error": str(e)}),
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
