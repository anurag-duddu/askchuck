"""
CLI script for building Pinecone index.
Processes all chunks through embedding and indexing pipeline.
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.indexing.pipeline import IndexingPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Build Pinecone hybrid search index from chunks"
    )

    parser.add_argument(
        "--all", action="store_true", help="Index all chunks"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of documents to index",
    )

    args = parser.parse_args()

    # Create pipeline
    pipeline = IndexingPipeline()

    try:
        if args.all:
            # Index all chunks
            logger.info("Indexing all chunks")
            stats = pipeline.index_all_chunks()

        elif args.limit:
            # Index limited number of documents
            logger.info(f"Indexing chunks from {args.limit} documents")
            stats = pipeline.index_all_chunks(limit=args.limit)

        else:
            # Default: index first 2 documents for testing
            logger.info("No arguments specified. Indexing first 2 documents (test mode)")
            logger.info("Use --all to index all chunks, or --limit N for N documents")
            stats = pipeline.index_all_chunks(limit=2)

        logger.info("\n✓ Indexing complete!")
        logger.info(f"\nStatistics:")
        logger.info(f"  Total indexed: {stats['total_indexed']}")
        logger.info(f"  Parent chunks: {stats['parent_chunks']}")
        logger.info(f"  Child chunks: {stats['child_chunks']}")
        logger.info(f"  Figure chunks: {stats['figure_chunks']}")

    except Exception as e:
        logger.error(f"\n✗ Indexing failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
