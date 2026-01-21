"""
Pinecone native hybrid search retriever.
Queries the Pinecone index with both dense (Voyage AI) and sparse (BM25) vectors.
"""

import logging
from typing import Dict, List, Optional

from pinecone import Pinecone

from src.indexing.embeddings import VoyageEmbedder
from src.indexing.sparse_encoder import SparseEncoder
from src.utils.config import settings

logger = logging.getLogger(__name__)


class PineconeHybridRetriever:
    """
    Retrieves chunks using Pinecone's native hybrid search.

    Combines dense (Voyage AI) and sparse (BM25) vectors in a single query.
    Pinecone automatically handles RRF fusion internally.
    """

    def __init__(
        self,
        alpha: float = 0.5,
        expand_to_parents: bool = True,
        expansion_threshold: float = 0.7,
    ):
        """
        Initialize the Pinecone hybrid retriever.

        Args:
            alpha: Dense/sparse weighting (0.0=pure BM25, 1.0=pure semantic)
            expand_to_parents: Whether to add parent chunks to child results
            expansion_threshold: Min score to trigger parent expansion
        """
        # Initialize Pinecone
        pc = Pinecone(api_key=settings.pinecone_api_key)
        self.index = pc.Index(settings.pinecone_index_name)

        # Initialize embedding and sparse encoding
        self.embedder = VoyageEmbedder()
        self.sparse_encoder = SparseEncoder()
        self.sparse_encoder.load()  # Load saved encoder from PRD-04

        self.alpha = alpha
        self.expand_to_parents = expand_to_parents
        self.expansion_threshold = expansion_threshold

        logger.info(f"PineconeHybridRetriever initialized (alpha={alpha})")

    def retrieve(
        self,
        query: str,
        top_k: int = 50,
        filter: Optional[Dict] = None,
        include_metadata: bool = True,
    ) -> List[Dict]:
        """
        Retrieve relevant chunks using hybrid search.

        Args:
            query: The search query
            top_k: Number of results to return
            filter: Metadata filter dict (e.g., {"chunk_type": "text"})
            include_metadata: Whether to include full metadata

        Returns:
            List of result dictionaries with scores and metadata
        """
        # Generate dense vector
        dense_vector = self.embedder.embed_query(query)

        # Generate sparse vector
        sparse_vector = self.sparse_encoder.encode(query)

        # Query Pinecone with hybrid search
        results = self.index.query(
            vector=dense_vector,
            sparse_vector=sparse_vector,
            top_k=top_k,
            filter=filter,
            include_metadata=include_metadata,
        )

        # Convert to standard format
        candidates = []
        for match in results.matches:
            candidate = {
                "chunk_id": match.id,
                "score": match.score,
                "metadata": match.metadata if include_metadata else {},
            }

            # Extract text from metadata
            if include_metadata:
                candidate["content"] = match.metadata.get("text", "")

            candidates.append(candidate)

        logger.info(
            f"Retrieved {len(candidates)} candidates for query: '{query[:50]}...'"
        )

        return candidates

    def retrieve_with_expansion(
        self, query: str, top_k: int = 50, filter: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Retrieve with optional parent-child expansion.

        Args:
            query: The search query
            top_k: Number of initial candidates
            filter: Metadata filter dict

        Returns:
            List of candidates including expanded parents
        """
        # Initial retrieval
        candidates = self.retrieve(query, top_k, filter)

        if not self.expand_to_parents:
            return candidates

        # Identify high-scoring child chunks
        parent_ids = set()
        for chunk in candidates:
            metadata = chunk.get("metadata", {})
            chunk_level = metadata.get("level")
            parent_id = metadata.get("parent_id")

            # Expand if child chunk with high relevance
            if (
                chunk_level == "child"
                and parent_id
                and chunk["score"] >= self.expansion_threshold
            ):

                # Check if parent already in results
                if parent_id not in [c["chunk_id"] for c in candidates]:
                    parent_ids.add(parent_id)

        if not parent_ids:
            logger.debug("No parent expansion needed")
            return candidates

        # Fetch parent chunks by ID
        logger.info(f"Expanding to {len(parent_ids)} parent chunks")
        fetch_response = self.index.fetch(ids=list(parent_ids))

        # Add parents to candidate pool
        for parent_id, vector_data in fetch_response.vectors.items():
            parent_chunk = {
                "chunk_id": parent_id,
                "score": 0.0,  # Parent has no retrieval score initially
                "metadata": vector_data.metadata,
                "content": vector_data.metadata.get("text", ""),
                "expanded_parent": True,  # Flag for debugging
            }
            candidates.append(parent_chunk)

        logger.info(
            f"Expanded candidates: {len(candidates)} total (added {len(parent_ids)} parents)"
        )

        return candidates

    def retrieve_figures(self, query: str, top_k: int = 5) -> List[Dict]:
        """Convenience method to retrieve only figure chunks."""
        filter = {"chunk_type": "figure"}
        return self.retrieve(query, top_k, filter)

    def retrieve_from_document(
        self, query: str, document_id: str, top_k: int = 10
    ) -> List[Dict]:
        """Convenience method to retrieve within a specific document."""
        filter = {"document_id": document_id}
        return self.retrieve(query, top_k, filter)

    def fetch_neighbors(self, chunk_id: str) -> List[Dict]:
        """
        Fetch neighboring chunks for contextual expansion.

        Args:
            chunk_id: The chunk ID to fetch neighbors for

        Returns:
            List of neighbor chunks
        """
        # Fetch the chunk
        response = self.index.fetch(ids=[chunk_id])

        if not response.vectors:
            logger.warning(f"Chunk not found: {chunk_id}")
            return []

        chunk_data = response.vectors[chunk_id]
        neighbor_ids = chunk_data.metadata.get("neighbor_chunk_ids", "")

        if not neighbor_ids:
            return []

        # Parse comma-separated neighbor IDs
        if isinstance(neighbor_ids, str):
            neighbor_id_list = [
                n.strip() for n in neighbor_ids.split(",") if n.strip()
            ]
        else:
            neighbor_id_list = neighbor_ids

        if not neighbor_id_list:
            return []

        # Fetch neighbors
        neighbors_response = self.index.fetch(ids=neighbor_id_list)

        neighbors = []
        for neighbor_id, vector_data in neighbors_response.vectors.items():
            neighbor = {
                "chunk_id": neighbor_id,
                "metadata": vector_data.metadata,
                "content": vector_data.metadata.get("text", ""),
            }
            neighbors.append(neighbor)

        logger.debug(f"Fetched {len(neighbors)} neighbors for {chunk_id}")
        return neighbors


# Global instance
_retriever: Optional[PineconeHybridRetriever] = None


def get_retriever(alpha: float = 0.5) -> PineconeHybridRetriever:
    """Get or create the global retriever instance."""
    global _retriever
    if _retriever is None:
        _retriever = PineconeHybridRetriever(alpha=alpha)
    return _retriever
