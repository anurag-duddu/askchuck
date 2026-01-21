"""
Cross-encoder reranking using Cohere's rerank API.
Provides more accurate relevance scoring for top candidates.
"""

import logging
from typing import Dict, List, Optional

import cohere

from src.utils.config import settings

logger = logging.getLogger(__name__)


class CohereReranker:
    """
    Reranks retrieval results using Cohere's cross-encoder model.

    Cross-encoders process query and document together, enabling
    deeper semantic understanding than bi-encoder embeddings.
    We use this as a second stage after Pinecone hybrid retrieval
    to improve precision on the top results.
    """

    def __init__(self, model: str = "rerank-english-v3.0"):
        """
        Initialize the Cohere reranker.

        Args:
            model: Cohere rerank model name
        """
        self.client = cohere.Client(api_key=settings.cohere_api_key)
        self.model = model

        logger.info(f"CohereReranker initialized with model: {self.model}")

    def rerank(
        self, query: str, results: List[Dict], top_k: int = 5
    ) -> List[Dict]:
        """
        Rerank retrieval results using cross-encoder scoring.

        Args:
            query: The search query
            results: List of retrieval results with 'content' field
            top_k: Number of results to return after reranking

        Returns:
            Reranked results with relevance scores
        """
        if not results:
            return []

        # Extract documents for reranking
        documents = []
        for r in results:
            content = r.get("content", "")
            # Truncate very long documents (Cohere has limits)
            if len(content) > 4000:
                content = content[:4000] + "..."
            documents.append(content)

        try:
            response = self.client.rerank(
                model=self.model,
                query=query,
                documents=documents,
                top_n=min(top_k, len(documents)),
                return_documents=False,  # We already have the documents
            )

            # Build reranked results
            reranked = []
            for i, r in enumerate(response.results):
                original_result = results[r.index].copy()
                original_result["rerank_score"] = r.relevance_score
                original_result["rerank_rank"] = i + 1
                original_result["original_rank"] = r.index + 1
                reranked.append(original_result)

            logger.info(f"Reranked {len(results)} results to top {len(reranked)}")

            return reranked

        except Exception as e:
            logger.error(f"Cohere rerank failed: {e}. Returning original order.")
            return results[:top_k]

    def rerank_with_context(
        self, query: str, results: List[Dict], context: str = "", top_k: int = 5
    ) -> List[Dict]:
        """
        Rerank with additional context (e.g., conversation history).

        The context is prepended to the query to provide additional
        signals for relevance scoring.

        Args:
            query: The search query
            results: List of retrieval results
            context: Additional context (e.g., conversation history)
            top_k: Number of results to return

        Returns:
            Reranked results
        """
        if context:
            enhanced_query = f"{context}\n\nCurrent question: {query}"
        else:
            enhanced_query = query

        return self.rerank(enhanced_query, results, top_k)


# Global instance
_reranker: Optional[CohereReranker] = None


def get_reranker() -> CohereReranker:
    """Get or create the global reranker instance."""
    global _reranker
    if _reranker is None:
        _reranker = CohereReranker()
    return _reranker


def rerank_results(query: str, results: List[Dict], top_k: int = 5) -> List[Dict]:
    """Convenience function to rerank results."""
    return get_reranker().rerank(query, results, top_k)
