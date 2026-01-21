"""
CLI script for document ingestion pipeline.
Processes PDF documents through parsing, figure extraction, and description.
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.pipeline import DocumentIngestionPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Process PDF documents through the ingestion pipeline"
    )

    parser.add_argument(
        "--all", action="store_true", help="Process all PDFs in data/raw/"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of documents to process",
    )

    parser.add_argument(
        "--pdf",
        type=str,
        default=None,
        help="Path to a single PDF to process",
    )

    parser.add_argument(
        "--skip-figures",
        action="store_true",
        help="Skip figure extraction (text only)",
    )

    parser.add_argument(
        "--skip-descriptions",
        action="store_true",
        help="Skip vision model descriptions",
    )

    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Skip Cloudflare R2 upload",
    )

    args = parser.parse_args()

    # Create pipeline
    pipeline = DocumentIngestionPipeline(
        skip_figures=args.skip_figures,
        skip_descriptions=args.skip_descriptions,
        skip_upload=args.skip_upload,
    )

    try:
        if args.pdf:
            # Process single PDF
            logger.info(f"Processing single PDF: {args.pdf}")
            pipeline.process_document(Path(args.pdf))

        elif args.all or args.limit:
            # Process all/limited PDFs
            limit = args.limit if args.limit else None
            logger.info(f"Processing PDFs (limit: {limit or 'all'})")
            pipeline.process_all_documents(limit=limit)

        else:
            # Default: process first 2 for testing
            logger.info("No arguments specified. Processing first 2 PDFs (test mode)")
            logger.info("Use --all to process all PDFs, or --pdf <path> for one PDF")
            pipeline.process_all_documents(limit=2)

        logger.info("\n✓ Ingestion complete!")

    except Exception as e:
        logger.error(f"\n✗ Ingestion failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
