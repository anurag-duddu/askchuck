"""
CLI script for chunking pipeline.
Processes documents through semantic chunking, figure chunking, and enrichment.
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.chunking.pipeline import ChunkingPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Process documents through chunking pipeline"
    )

    parser.add_argument(
        "--all", action="store_true", help="Process all documents in data/processed/"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of documents to process",
    )

    parser.add_argument(
        "--doc",
        type=str,
        default=None,
        help="Path to a single document to process",
    )

    parser.add_argument(
        "--skip-enrichment",
        action="store_true",
        help="Skip contextual enrichment (faster)",
    )

    parser.add_argument(
        "--skip-figures",
        action="store_true",
        help="Skip figure chunk creation",
    )

    args = parser.parse_args()

    # Create pipeline
    pipeline = ChunkingPipeline(
        skip_enrichment=args.skip_enrichment,
        skip_figures=args.skip_figures,
    )

    try:
        if args.doc:
            # Process single document
            logger.info(f"Processing single document: {args.doc}")
            pipeline.process_document(Path(args.doc))

        elif args.all or args.limit:
            # Process all/limited documents
            limit = args.limit if args.limit else None
            logger.info(f"Processing documents (limit: {limit or 'all'})")
            pipeline.process_all_documents(limit=limit)

        else:
            # Default: process first 2 for testing
            logger.info("No arguments specified. Processing first 2 documents (test mode)")
            logger.info("Use --all to process all documents, or --doc <path> for one document")
            pipeline.process_all_documents(limit=2)

        logger.info("\n✓ Chunking complete!")

    except Exception as e:
        logger.error(f"\n✗ Chunking failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
