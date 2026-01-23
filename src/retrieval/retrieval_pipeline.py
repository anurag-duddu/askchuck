"""
Complete retrieval pipeline combining Pinecone hybrid search and Cohere reranking.
This is the main entry point for retrieval operations.
"""

import logging
import os
from typing import Dict, List, Optional

from src.retrieval.pinecone_retriever import (PineconeHybridRetriever,
                                              get_retriever)
from src.retrieval.query_expansion import QueryExpander, get_query_expander
from src.retrieval.reranker import CohereReranker, get_reranker
from src.utils.config import settings

logger = logging.getLogger(__name__)

# LangSmith tracing setup
try:
    from langsmith import traceable

    LANGSMITH_ENABLED = bool(settings.langchain_api_key)
    if LANGSMITH_ENABLED:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
except ImportError:
    LANGSMITH_ENABLED = False

    def traceable(*args, **kwargs):
        def decorator(func):
            return func

        return decorator if not args else args[0]


class RetrievalPipeline:
    """
    Complete retrieval pipeline for AskChuck.

    Combines:
    1. Optional query expansion (Owen terminology)
    2. Pinecone hybrid search (dense + sparse with auto-fusion)
    3. Optional parent-child expansion
    4. Cohere cross-encoder reranking

    This multi-stage approach retrieves broadly first (high recall)
    then refines with precise scoring (high precision).
    """

    def __init__(
        self,
        retriever: Optional[PineconeHybridRetriever] = None,
        reranker: Optional[CohereReranker] = None,
        query_expander: Optional[QueryExpander] = None,
        initial_k: int = 50,
        final_k: int = 5,
    ):
        """
        Initialize the retrieval pipeline.

        Args:
            retriever: Pinecone hybrid retriever instance
            reranker: Cohere reranker instance
            query_expander: Query expander instance
            initial_k: Number of candidates from Pinecone
            final_k: Number of results after reranking
        """
        self.retriever = retriever or get_retriever()
        self.reranker = reranker or get_reranker()
        self.query_expander = query_expander or get_query_expander()
        self.initial_k = initial_k
        self.final_k = final_k

        logger.info("RetrievalPipeline initialized")

    @traceable(name="retrieval_pipeline", run_type="retriever")
    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        expand_query: bool = False,
        expand_parents: bool = True,
        include_figures: bool = True,
        document_id: Optional[str] = None,
        skip_rerank: bool = False,
    ) -> List[Dict]:
        """
        Run the complete retrieval pipeline.

        Args:
            query: The search query
            top_k: Number of final results (default: self.final_k)
            expand_query: Whether to expand with Owen terminology
            expand_parents: Whether to add parent chunks to children
            include_figures: Whether to include figure chunks
            document_id: Filter to specific document
            skip_rerank: If True, skip reranking step

        Returns:
            List of relevant chunks with metadata and scores
        """
        top_k = top_k or self.final_k

        logger.info(f"Starting retrieval for query: '{query[:50]}...'")

        # Stage 0: Optional query expansion
        search_query = query
        if expand_query:
            search_query = self.query_expander.expand_query(query)
            logger.debug(f"Expanded query: '{search_query}'")

        # Stage 1: Pinecone hybrid retrieval
        filter_dict = {}
        if document_id:
            filter_dict["document_id"] = document_id

        if expand_parents:
            candidates = self.retriever.retrieve_with_expansion(
                search_query,
                top_k=self.initial_k,
                filter=filter_dict if filter_dict else None,
            )
        else:
            candidates = self.retriever.retrieve(
                search_query,
                top_k=self.initial_k,
                filter=filter_dict if filter_dict else None,
            )

        if not candidates:
            logger.warning(f"No candidates found for query: {query}")
            return []

        # Filter figures if requested
        if not include_figures:
            candidates = [
                c
                for c in candidates
                if c.get("metadata", {}).get("chunk_type") != "figure"
            ]

        logger.info(f"Retrieved {len(candidates)} candidates from Pinecone")

        # Stage 2: Reranking
        if skip_rerank or len(candidates) <= top_k:
            results = candidates[:top_k]
            logger.info(f"Skipping rerank, returning top {len(results)}")
        else:
            results = self.reranker.rerank(query, candidates, top_k)
            logger.info(f"Reranked to top {len(results)} results")

        # Enrich results with display-friendly format
        enriched_results = self._enrich_results(results)

        return enriched_results

    def retrieve_with_figures(
        self,
        query: str,
        text_k: int = 3,
        figure_k: int = 2,
        expand_query: bool = False,
    ) -> Dict:
        """
        Retrieve both text and figure chunks separately.

        Useful for ensuring relevant figures are included
        even if they don't rank highest overall.

        Args:
            query: The search query
            text_k: Number of text chunks
            figure_k: Number of figure chunks
            expand_query: Whether to expand query

        Returns:
            Dict with 'text_chunks' and 'figure_chunks' lists
        """
        # Get text chunks (excluding figures)
        text_results = self.retrieve(
            query, top_k=text_k, expand_query=expand_query, include_figures=False
        )

        # Get figure chunks separately
        figure_results = self.retriever.retrieve_figures(query, top_k=figure_k)
        figure_results = self._enrich_results(figure_results)

        return {"text_chunks": text_results, "figure_chunks": figure_results}

    def retrieve_with_neighbors(
        self, query: str, top_k: Optional[int] = None, include_neighbors: bool = True
    ) -> Dict:
        """
        Retrieve chunks and optionally include neighboring chunks.

        Useful for reading coherent multi-chunk passages.

        Args:
            query: The search query
            top_k: Number of main results
            include_neighbors: Whether to fetch neighbors

        Returns:
            Dict with 'main_chunks' and 'neighbor_chunks'
        """
        # Get main results
        main_results = self.retrieve(query, top_k=top_k)

        if not include_neighbors:
            return {"main_chunks": main_results, "neighbor_chunks": []}

        # Fetch neighbors for top result
        neighbors = []
        if main_results:
            top_chunk_id = main_results[0]["chunk_id"]
            neighbors = self.retriever.fetch_neighbors(top_chunk_id)
            neighbors = self._enrich_results(neighbors)

        return {"main_chunks": main_results, "neighbor_chunks": neighbors}

    def _enrich_results(self, results: List[Dict]) -> List[Dict]:
        """Add display-friendly fields to results."""
        enriched = []

        for r in results:
            result = r.copy()
            metadata = result.get("metadata", {})

            # Add convenience fields
            result["document_title"] = metadata.get("document_title", "Unknown")
            result["section"] = metadata.get("source_section", "")
            result["chunk_type"] = metadata.get("chunk_type", "text")
            result["chunk_level"] = metadata.get("level", "child")

            # Handle figures specially
            if result["chunk_type"] == "figure":
                result["figure_url"] = metadata.get("figure_url", "")
                result["figure_caption"] = result.get("content", "")
                result["figure_number"] = metadata.get("figure_number", 0)

            # Owen terms for display
            owen_terms = metadata.get("owen_terms", [])
            if isinstance(owen_terms, str):
                result["owen_terms"] = owen_terms.split(",") if owen_terms else []
            else:
                result["owen_terms"] = owen_terms or []

            # Parent/child info
            result["parent_id"] = metadata.get("parent_id", "")

            enriched.append(result)

        return enriched


# Global instance
_pipeline: Optional[RetrievalPipeline] = None


def get_retrieval_pipeline() -> RetrievalPipeline:
    """Get or create the global retrieval pipeline instance."""
    global _pipeline
    if _pipeline is None:
        _pipeline = RetrievalPipeline()
    return _pipeline


def retrieve(query: str, top_k: int = 5, expand_query: bool = False) -> List[Dict]:
    """Convenience function to run retrieval."""
    return get_retrieval_pipeline().retrieve(
        query, top_k=top_k, expand_query=expand_query
    )
