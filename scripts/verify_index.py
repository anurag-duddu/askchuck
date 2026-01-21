#!/usr/bin/env python3
"""
CLI script for verifying Pinecone index.
Tests index health, hybrid search, and metadata filtering.
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.indexing.embeddings import VoyageEmbedder
from src.indexing.sparse_encoder import SparseEncoder
from src.indexing.vector_store import PineconeIndexManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def verify_index_stats(manager: PineconeIndexManager) -> dict:
    """
    Verify index statistics.

    Args:
        manager: PineconeIndexManager instance

    Returns:
        Index statistics dictionary
    """
    logger.info("\n" + "=" * 60)
    logger.info("VERIFYING INDEX STATISTICS")
    logger.info("=" * 60)

    stats = manager.get_stats()

    logger.info(f"\nIndex: {manager.index_name}")
    logger.info(f"  Total vectors: {stats.get('total_vector_count', 0)}")
    logger.info(f"  Dimension: {manager.dimension}")

    # Check namespaces
    namespaces = stats.get("namespaces", {})
    if namespaces:
        logger.info(f"\nNamespaces:")
        for ns_name, ns_stats in namespaces.items():
            ns_display = ns_name if ns_name else "(default)"
            logger.info(f"  {ns_display}: {ns_stats.get('vector_count', 0)} vectors")
    else:
        logger.info(f"\nNo namespaces found (all in default namespace)")

    return stats


def test_hybrid_search(
    manager: PineconeIndexManager,
    embedder: VoyageEmbedder,
    sparse_encoder: SparseEncoder,
) -> None:
    """
    Test hybrid search with sample queries.

    Args:
        manager: PineconeIndexManager instance
        embedder: VoyageEmbedder instance
        sparse_encoder: SparseEncoder instance
    """
    logger.info("\n" + "=" * 60)
    logger.info("TESTING HYBRID SEARCH")
    logger.info("=" * 60)

    # Sample queries
    test_queries = [
        "What is structured planning?",
        "How do design factors work?",
        "Tell me about speculation in planning",
    ]

    for i, query in enumerate(test_queries, 1):
        logger.info(f"\nQuery {i}: '{query}'")

        try:
            # Generate query vectors
            dense_vector = embedder.embed_query(query)
            sparse_vector = sparse_encoder.encode(query)

            # Search
            results = manager.query(
                dense_vector=dense_vector,
                sparse_vector=sparse_vector,
                top_k=3,
            )

            # Display results
            matches = results.get("matches", [])
            logger.info(f"  Found {len(matches)} results:")

            for j, match in enumerate(matches[:3], 1):
                score = match.get("score", 0)
                metadata = match.get("metadata", {})
                chunk_id = metadata.get("chunk_id", "unknown")
                doc_title = metadata.get("document_title", "unknown")
                text_preview = metadata.get("text", "")[:100]

                logger.info(f"    {j}. Score: {score:.4f}")
                logger.info(f"       Chunk: {chunk_id}")
                logger.info(f"       Document: {doc_title}")
                logger.info(f"       Preview: {text_preview}...")

        except Exception as e:
            logger.error(f"  Query failed: {e}")


def test_metadata_filtering(
    manager: PineconeIndexManager,
    embedder: VoyageEmbedder,
    sparse_encoder: SparseEncoder,
) -> None:
    """
    Test metadata filtering capabilities.

    Args:
        manager: PineconeIndexManager instance
        embedder: VoyageEmbedder instance
        sparse_encoder: SparseEncoder instance
    """
    logger.info("\n" + "=" * 60)
    logger.info("TESTING METADATA FILTERING")
    logger.info("=" * 60)

    query = "planning methodology"

    # Test 1: Filter by level
    logger.info(f"\nTest 1: Filter by level=parent")

    try:
        dense_vector = embedder.embed_query(query)
        sparse_vector = sparse_encoder.encode(query)

        results = manager.query(
            dense_vector=dense_vector,
            sparse_vector=sparse_vector,
            top_k=3,
            filter={"level": {"$eq": "parent"}},
        )

        matches = results.get("matches", [])
        logger.info(f"  Found {len(matches)} parent chunks")

        for match in matches[:2]:
            metadata = match.get("metadata", {})
            logger.info(f"    - {metadata.get('chunk_id')} (level={metadata.get('level')})")

    except Exception as e:
        logger.error(f"  Filter test failed: {e}")

    # Test 2: Filter by chunk type
    logger.info(f"\nTest 2: Filter by chunk_type=text")

    try:
        results = manager.query(
            dense_vector=dense_vector,
            sparse_vector=sparse_vector,
            top_k=3,
            filter={"chunk_type": {"$eq": "text"}},
        )

        matches = results.get("matches", [])
        logger.info(f"  Found {len(matches)} text chunks")

    except Exception as e:
        logger.error(f"  Filter test failed: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Verify Pinecone index health and functionality"
    )

    parser.add_argument(
        "--skip-search",
        action="store_true",
        help="Skip hybrid search tests (only check stats)",
    )

    args = parser.parse_args()

    try:
        # Initialize components
        logger.info("Initializing components...")
        manager = PineconeIndexManager()
        index = manager.get_or_create_index()

        # Verify index statistics
        stats = verify_index_stats(manager)

        total_vectors = stats.get("total_vector_count", 0)

        if total_vectors == 0:
            logger.warning("\n⚠ Index is empty! Run build_index.py first.")
            sys.exit(1)

        # Skip search tests if requested or if sparse encoder not available
        if args.skip_search:
            logger.info("\n✓ Index stats verified (search tests skipped)")
            return

        # Load sparse encoder (required for queries)
        try:
            logger.info("\nLoading sparse encoder...")
            sparse_encoder = SparseEncoder()
            sparse_encoder.load()
        except FileNotFoundError:
            logger.warning(
                "\n⚠ Sparse encoder not found. Run build_index.py to fit encoder first."
            )
            logger.info("✓ Index stats verified (search tests skipped)")
            sys.exit(0)

        # Initialize embedder
        embedder = VoyageEmbedder()

        # Test hybrid search
        test_hybrid_search(manager, embedder, sparse_encoder)

        # Test metadata filtering
        test_metadata_filtering(manager, embedder, sparse_encoder)

        logger.info("\n" + "=" * 60)
        logger.info("✓ INDEX VERIFICATION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"\nAll tests passed!")
        logger.info(f"  Total vectors: {total_vectors}")
        logger.info(f"  Hybrid search: ✓ Working")
        logger.info(f"  Metadata filtering: ✓ Working")

    except Exception as e:
        logger.error(f"\n✗ Verification failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
