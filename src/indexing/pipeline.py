"""
Main indexing pipeline.
Orchestrates embedding generation, sparse encoding, and Pinecone upsertion.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from tqdm import tqdm

from src.indexing.embeddings import VoyageEmbedder
from src.indexing.sparse_encoder import SparseEncoder
from src.indexing.vector_store import PineconeIndexManager
from src.utils.config import CHUNKS_DIR

logger = logging.getLogger(__name__)


class IndexingPipeline:
    """
    Complete indexing pipeline for chunks.
    Generates embeddings, sparse vectors, and indexes in Pinecone.
    """

    def __init__(self):
        """Initialize the indexing pipeline."""
        self.embedder = VoyageEmbedder()
        self.sparse_encoder = SparseEncoder()
        self.index_manager = PineconeIndexManager()

        logger.info("Indexing pipeline initialized")

    def index_all_chunks(self, limit: Optional[int] = None) -> Dict:
        """
        Index all chunks from chunking phase.

        Args:
            limit: Optional limit on number of documents to index

        Returns:
            Indexing statistics
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"STARTING INDEXING PIPELINE")
        logger.info(f"{'='*60}")

        # Step 1: Load all chunks
        logger.info("Step 1/5: Loading chunks...")
        all_chunks = self._load_all_chunks(limit=limit)
        logger.info(f"  Loaded {len(all_chunks)} chunks from {len(set(c['document_id'] for c in all_chunks))} documents")

        # Step 2: Fit sparse encoder on corpus
        logger.info("Step 2/5: Fitting sparse encoder...")
        chunk_texts = [chunk.get("enriched_text") or chunk.get("text") for chunk in all_chunks]
        self.sparse_encoder.fit(chunk_texts)
        self.sparse_encoder.save()
        logger.info("  ✓ Sparse encoder fitted and saved")

        # Step 3: Generate dense embeddings
        logger.info("Step 3/5: Generating dense embeddings...")
        dense_embeddings = self.embedder.embed_chunks(all_chunks)
        logger.info(f"  ✓ Generated {len(dense_embeddings)} dense embeddings")

        # Step 4: Generate sparse vectors
        logger.info("Step 4/5: Generating sparse vectors...")
        sparse_vectors = self.sparse_encoder.encode_batch(chunk_texts)
        logger.info(f"  ✓ Generated {len(sparse_vectors)} sparse vectors")

        # Step 5: Index in Pinecone
        logger.info("Step 5/5: Indexing in Pinecone...")
        stats = self._index_in_pinecone(all_chunks, dense_embeddings, sparse_vectors)

        logger.info(f"\n{'='*60}")
        logger.info(f"INDEXING COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"Total chunks indexed: {stats['total_indexed']}")
        logger.info(f"  Parent chunks: {stats['parent_chunks']}")
        logger.info(f"  Child chunks: {stats['child_chunks']}")
        logger.info(f"  Figure chunks: {stats['figure_chunks']}")

        return stats

    def _load_all_chunks(self, limit: Optional[int] = None) -> List[dict]:
        """
        Load all chunks from chunk files.

        Args:
            limit: Optional limit on number of documents

        Returns:
            List of all chunks
        """
        chunk_files = sorted(CHUNKS_DIR.glob("*_chunks.json"))

        if limit:
            chunk_files = chunk_files[:limit]

        all_chunks = []

        for chunk_file in tqdm(chunk_files, desc="Loading chunks", unit="doc"):
            with open(chunk_file, "r", encoding="utf-8") as f:
                chunks = json.load(f)
                all_chunks.extend(chunks)

        return all_chunks

    def _index_in_pinecone(
        self,
        chunks: List[dict],
        dense_embeddings: List[List[float]],
        sparse_vectors: List[Dict],
    ) -> Dict:
        """
        Index chunks in Pinecone with hybrid vectors.

        Args:
            chunks: List of chunk dictionaries
            dense_embeddings: List of dense vectors
            sparse_vectors: List of sparse vectors

        Returns:
            Indexing statistics
        """
        # Get or create index
        index = self.index_manager.get_or_create_index()

        # Prepare vectors for upsertion
        vectors_to_upsert = []

        for i, chunk in enumerate(chunks):
            # Prepare metadata (Pinecone has size limits)
            metadata = self._prepare_metadata(chunk)

            # Create vector tuple
            vec_tuple = (
                chunk["chunk_id"],  # ID
                dense_embeddings[i],  # Dense vector
                sparse_vectors[i],  # Sparse vector
                metadata,  # Metadata
            )

            vectors_to_upsert.append(vec_tuple)

        # Upsert to Pinecone
        self.index_manager.upsert_vectors(vectors_to_upsert)

        # Calculate statistics
        stats = {
            "total_indexed": len(chunks),
            "parent_chunks": sum(1 for c in chunks if c.get("level") == "parent"),
            "child_chunks": sum(1 for c in chunks if c.get("level") == "child"),
            "figure_chunks": sum(1 for c in chunks if c.get("level") == "figure"),
        }

        return stats

    def _prepare_metadata(self, chunk: dict) -> Dict:
        """
        Prepare chunk metadata for Pinecone.
        Pinecone has size limits, so we keep only essential fields.

        Args:
            chunk: Chunk dictionary

        Returns:
            Filtered metadata dictionary
        """
        metadata = {
            "chunk_id": chunk["chunk_id"],
            "document_id": chunk["document_id"],
            "level": chunk.get("level", "child"),
            "chunk_position": chunk.get("chunk_position", 0),
            # Document metadata
            "document_title": chunk["metadata"].get("document_title", ""),
            "document_author": chunk["metadata"].get("document_author", ""),
            # Chunk metadata
            "source_section": chunk["metadata"].get("source_section", ""),
            "owen_terms": chunk["metadata"].get("owen_terms", [])[:10],  # Limit array size
            # Hierarchical metadata
            "parent_id": chunk["metadata"].get("parent_id", ""),
            # Figure metadata (if applicable)
            "chunk_type": chunk["metadata"].get("chunk_type", "text"),
            "figure_number": chunk["metadata"].get("figure_number", 0),
            "figure_url": chunk["metadata"].get("figure_url", ""),
            # Text (for display in results)
            "text": chunk["text"][:1000],  # Truncate for size
        }

        # Remove empty/null values
        metadata = {k: v for k, v in metadata.items() if v not in [None, "", [], 0] or k in ["chunk_position", "figure_number"]}

        return metadata


def index_all_chunks(limit: Optional[int] = None) -> Dict:
    """Convenience function to run full indexing pipeline."""
    pipeline = IndexingPipeline()
    return pipeline.index_all_chunks(limit=limit)
