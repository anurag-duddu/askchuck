"""
Pydantic models for API request/response validation.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


# Request models
class QueryRequest(BaseModel):
    """Request model for query endpoints."""

    question: str = Field(..., description="User's question", min_length=1)
    session_id: Optional[str] = Field(None, description="Optional session ID for tracking")
    conversation_history: List[dict] = Field(
        default_factory=list,
        description="Previous conversation messages",
    )
    include_figures: bool = Field(True, description="Whether to retrieve figures")
    top_k: int = Field(5, description="Number of chunks to retrieve", ge=1, le=20)


# Response models
class Source(BaseModel):
    """Source citation model."""

    display: str = Field(..., description="Display format [Document, Section]")
    document: str = Field(..., description="Document title")
    section: str = Field(..., description="Section name")
    chunk_id: str = Field(..., description="Chunk ID for debugging")
    chunk_level: str = Field(..., description="Chunk level (parent/child)")


class Figure(BaseModel):
    """Figure model."""

    url: str = Field(..., description="Cloudflare R2 URL")
    caption: str = Field("", description="Figure caption")
    document: str = Field(..., description="Source document")
    figure_number: int = Field(..., description="Figure number")
    description: str = Field("", description="Figure description")


class QueryResponse(BaseModel):
    """Response model for non-streaming query."""

    answer: str = Field(..., description="Generated response")
    sources: List[Source] = Field(..., description="Source citations")
    chunk_ids: List[str] = Field(..., description="Chunk IDs used")
    figures: List[Figure] = Field(..., description="Relevant figures")
    chunks_used: int = Field(..., description="Number of chunks retrieved")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    rag_available: bool = Field(..., description="RAG chain availability")
