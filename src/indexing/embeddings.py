"""
Dense embedding generation using Voyage AI.
Generates 1024-dimensional embeddings optimized for RAG retrieval.
"""

import logging
import time
from typing import List

import voyageai

from src.utils.config import settings

logger = logging.getLogger(__name__)


class VoyageEmbedder:
    """
    Generates dense embeddings using Voyage AI voyage-3 model.
    Optimized for RAG retrieval tasks.
    """

    def __init__(self):
        """Initialize the Voyage AI embedder."""
        self.client = voyageai.Client(api_key=settings.voyage_api_key)
        self.model = settings.voyage_model  # voyage-3

        # Embedding parameters
        self.dimension = 1024  # voyage-3 dimension
        self.batch_size = 128  # Voyage AI batch limit

    def embed_texts(
        self,
        texts: List[str],
        input_type: str = "document",
        show_progress: bool = True,
    ) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed
            input_type: "document" for chunks, "query" for search queries
            show_progress: Show progress logging

        Returns:
            List of embedding vectors (each 1024-dim)
        """
        if not texts:
            return []

        logger.info(f"Generating {len(texts)} embeddings (input_type={input_type})...")

        all_embeddings = []

        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(texts) + self.batch_size - 1) // self.batch_size

            if show_progress:
                logger.info(f"  Batch {batch_num}/{total_batches}: {len(batch)} texts")

            try:
                # Call Voyage AI API
                result = self.client.embed(
                    batch, model=self.model, input_type=input_type
                )

                # Extract embeddings
                batch_embeddings = result.embeddings

                all_embeddings.extend(batch_embeddings)

                # Rate limiting (safe delay between batches)
                # Free tier: 3 RPM = need 20s between requests
                if i + self.batch_size < len(texts):
                    delay = 21  # 21 seconds for 3 RPM limit
                    logger.info(f"  Waiting {delay}s (rate limit)...")
                    time.sleep(delay)

            except Exception as e:
                logger.error(f"Embedding batch {batch_num} failed: {e}")
                # Retry once with exponential backoff
                try:
                    retry_delay = 25  # Wait longer for rate limit reset
                    logger.info(f"  Retrying after {retry_delay}s...")
                    time.sleep(retry_delay)
                    result = self.client.embed(
                        batch, model=self.model, input_type=input_type
                    )
                    all_embeddings.extend(result.embeddings)
                except Exception as retry_error:
                    logger.error(f"Retry failed: {retry_error}")
                    raise

        logger.info(f"✓ Generated {len(all_embeddings)} embeddings")
        return all_embeddings

    def embed_chunks(self, chunks: List[dict]) -> List[List[float]]:
        """
        Generate embeddings for chunk dictionaries.

        Args:
            chunks: List of chunk dicts with 'enriched_text' field

        Returns:
            List of embedding vectors
        """
        # Extract enriched text from chunks
        texts = [chunk.get("enriched_text") or chunk.get("text") for chunk in chunks]

        # Embed with document input type
        embeddings = self.embed_texts(texts, input_type="document")

        return embeddings

    def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a search query.

        Args:
            query: Search query string

        Returns:
            Query embedding vector (1024-dim)
        """
        result = self.client.embed([query], model=self.model, input_type="query")
        return result.embeddings[0]


def embed_texts(texts: List[str], input_type: str = "document") -> List[List[float]]:
    """Convenience function to embed texts."""
    embedder = VoyageEmbedder()
    return embedder.embed_texts(texts, input_type=input_type)


def embed_chunks(chunks: List[dict]) -> List[List[float]]:
    """Convenience function to embed chunks."""
    embedder = VoyageEmbedder()
    return embedder.embed_chunks(chunks)


def embed_query(query: str) -> List[float]:
    """Convenience function to embed a query."""
    embedder = VoyageEmbedder()
    return embedder.embed_query(query)
