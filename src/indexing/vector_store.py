"""
Pinecone vector store management.
Creates and manages the hybrid search index.
"""

import logging
import time
from typing import Dict, List, Optional

from pinecone import Pinecone, ServerlessSpec

from src.utils.config import settings

logger = logging.getLogger(__name__)


class PineconeIndexManager:
    """
    Manages Pinecone index for hybrid search.
    Handles index creation, connection, and upsertion.
    """

    def __init__(self):
        """Initialize Pinecone client."""
        self.client = Pinecone(api_key=settings.pinecone_api_key)
        self.index_name = settings.pinecone_index_name
        self.dimension = 1024  # Voyage AI voyage-3 dimension
        self.index = None

    def get_or_create_index(self):
        """
        Get existing index or create new one.

        Returns:
            Pinecone Index object
        """
        # Check if index exists
        existing_indexes = self.client.list_indexes()
        index_names = [idx["name"] for idx in existing_indexes]

        if self.index_name in index_names:
            logger.info(f"Connecting to existing index: {self.index_name}")
            self.index = self.client.Index(self.index_name)
        else:
            logger.info(f"Creating new index: {self.index_name}")
            self._create_index()

        return self.index

    def _create_index(self):
        """Create new Pinecone serverless index with hybrid search support."""
        # Create serverless index with dotproduct metric for hybrid search
        self.client.create_index(
            name=self.index_name,
            dimension=self.dimension,
            metric="dotproduct",  # Required for sparse vector support
            spec=ServerlessSpec(
                cloud="aws",
                region=settings.pinecone_environment or "us-east-1",
            ),
        )

        # Wait for index to be ready
        logger.info("Waiting for index to be ready...")
        time.sleep(10)  # Initial wait

        # Connect to index
        self.index = self.client.Index(self.index_name)

        logger.info(f"✓ Index created: {self.index_name}")

    def upsert_vectors(
        self,
        vectors: List[tuple],
        namespace: str = "",
        batch_size: int = 100,
        show_progress: bool = True,
    ) -> Dict:
        """
        Upsert vectors to index.

        Args:
            vectors: List of (id, dense_vector, sparse_vector, metadata) tuples
            namespace: Optional namespace
            batch_size: Batch size for upsertion
            show_progress: Show progress logging

        Returns:
            Upsert stats dictionary
        """
        if not self.index:
            raise ValueError("Index not initialized. Call get_or_create_index() first.")

        logger.info(f"Upserting {len(vectors)} vectors to index...")

        total_upserted = 0

        # Process in batches
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i : i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(vectors) + batch_size - 1) // batch_size

            if show_progress:
                logger.info(
                    f"  Batch {batch_num}/{total_batches}: {len(batch)} vectors"
                )

            try:
                # Prepare batch for Pinecone format
                formatted_batch = []
                for vec_id, dense, sparse, metadata in batch:
                    formatted_batch.append(
                        {
                            "id": vec_id,
                            "values": dense,
                            "sparse_values": sparse,
                            "metadata": metadata,
                        }
                    )

                # Upsert batch
                self.index.upsert(vectors=formatted_batch, namespace=namespace)

                total_upserted += len(batch)

                # Small delay between batches
                if i + batch_size < len(vectors):
                    time.sleep(0.2)

            except Exception as e:
                logger.error(f"Upsert batch {batch_num} failed: {e}")
                raise

        logger.info(f"✓ Upserted {total_upserted} vectors")

        return {"upserted": total_upserted}

    def get_stats(self) -> Dict:
        """
        Get index statistics.

        Returns:
            Dictionary with index stats
        """
        if not self.index:
            raise ValueError("Index not initialized")

        stats = self.index.describe_index_stats()
        return stats

    def query(
        self,
        dense_vector: List[float],
        sparse_vector: Optional[Dict] = None,
        top_k: int = 10,
        filter: Optional[Dict] = None,
        namespace: str = "",
    ) -> Dict:
        """
        Query the index with hybrid search.

        Args:
            dense_vector: Dense query vector
            sparse_vector: Optional sparse query vector
            top_k: Number of results to return
            filter: Optional metadata filter
            namespace: Optional namespace

        Returns:
            Query results
        """
        if not self.index:
            raise ValueError("Index not initialized")

        query_params = {
            "vector": dense_vector,
            "top_k": top_k,
            "include_metadata": True,
            "namespace": namespace,
        }

        if sparse_vector:
            query_params["sparse_vector"] = sparse_vector

        if filter:
            query_params["filter"] = filter

        results = self.index.query(**query_params)

        return results


def create_index():
    """Convenience function to create index."""
    manager = PineconeIndexManager()
    return manager.get_or_create_index()


def get_index():
    """Convenience function to get existing index."""
    manager = PineconeIndexManager()
    manager.index = manager.client.Index(manager.index_name)
    return manager.index
