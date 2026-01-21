"""
Main document ingestion pipeline.
Orchestrates PDF parsing, figure extraction, description generation, and upload.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional

from tqdm import tqdm

from src.ingestion.figure_describer import FigureDescriber
from src.ingestion.figure_extractor import FigureExtractor
from src.ingestion.figure_uploader import R2Uploader
from src.ingestion.pdf_parser import OwenPDFParser
from src.utils.config import PROCESSED_DIR, RAW_DIR

logger = logging.getLogger(__name__)


class DocumentIngestionPipeline:
    """
    Complete document ingestion pipeline for Owen's papers.
    Processes PDFs through parsing, figure extraction, description, and upload.
    """

    def __init__(
        self,
        skip_figures: bool = False,
        skip_descriptions: bool = False,
        skip_upload: bool = False,
    ):
        """
        Initialize the ingestion pipeline.

        Args:
            skip_figures: Skip figure extraction (text only)
            skip_descriptions: Skip vision model descriptions
            skip_upload: Skip R2 upload
        """
        self.pdf_parser = OwenPDFParser()
        self.figure_extractor = FigureExtractor() if not skip_figures else None
        self.figure_describer = FigureDescriber() if not skip_descriptions else None
        self.figure_uploader = R2Uploader() if not skip_upload else None

        self.skip_figures = skip_figures
        self.skip_descriptions = skip_descriptions
        self.skip_upload = skip_upload

        logger.info("Document ingestion pipeline initialized")
        logger.info(f"  Figures: {'disabled' if skip_figures else 'enabled'}")
        logger.info(
            f"  Descriptions: {'disabled' if skip_descriptions else 'enabled'}"
        )
        logger.info(f"  R2 Upload: {'disabled' if skip_upload else 'enabled'}")

    def process_document(self, pdf_path: Path) -> dict:
        """
        Process a single PDF document through the full pipeline.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Complete document data dictionary
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {pdf_path.name}")
        logger.info(f"{'='*60}")

        # Step 1: Parse PDF text and metadata
        logger.info("Step 1/5: Parsing PDF...")
        doc_data = self.pdf_parser.parse_document(pdf_path)
        doc_id = doc_data["document_id"]

        # Step 2: Extract figures (if enabled)
        if not self.skip_figures:
            logger.info("Step 2/5: Extracting figures...")
            figures = self.figure_extractor.extract_figures(pdf_path, doc_id)
            doc_data["figures"] = figures
            logger.info(f"  Extracted {len(figures)} figures")
        else:
            logger.info("Step 2/5: Skipping figure extraction")
            doc_data["figures"] = []

        # Step 3: Generate figure descriptions (if enabled)
        if not self.skip_descriptions and doc_data["figures"]:
            logger.info("Step 3/5: Generating figure descriptions...")
            doc_data["figures"] = self.figure_describer.describe_figures_batch(
                doc_data["figures"]
            )
            logger.info(f"  Generated {len(doc_data['figures'])} descriptions")
        else:
            logger.info("Step 3/5: Skipping figure descriptions")

        # Step 4: Upload figures to R2 (if enabled)
        if not self.skip_upload and doc_data["figures"]:
            logger.info("Step 4/5: Uploading figures to R2...")
            doc_data["figures"] = self.figure_uploader.upload_figures_batch(
                doc_data["figures"]
            )
            logger.info(f"  Uploaded {len(doc_data['figures'])} figures")
        else:
            logger.info("Step 4/5: Skipping R2 upload")

        # Step 5: Save output JSON
        logger.info("Step 5/5: Saving output...")
        output_path = PROCESSED_DIR / f"{doc_id}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(doc_data, f, indent=2, ensure_ascii=False)

        logger.info(f"✓ Saved: {output_path.name}")
        logger.info(f"  Total pages: {doc_data['metadata']['total_pages']}")
        logger.info(f"  Total sections: {len(doc_data['sections'])}")
        logger.info(f"  Total figures: {len(doc_data['figures'])}")

        return doc_data

    def process_all_documents(self, limit: Optional[int] = None) -> List[dict]:
        """
        Process all PDF documents in the raw directory.

        Args:
            limit: Maximum number of documents to process (None for all)

        Returns:
            List of processed document data
        """
        pdf_files = sorted(RAW_DIR.glob("*.pdf"))

        if limit:
            pdf_files = pdf_files[:limit]

        logger.info(f"\n{'='*60}")
        logger.info(f"STARTING BATCH PROCESSING")
        logger.info(f"{'='*60}")
        logger.info(f"Found {len(pdf_files)} PDF files to process")

        results = []
        failed = []

        # Process with progress bar
        for pdf_path in tqdm(pdf_files, desc="Processing PDFs", unit="doc"):
            try:
                doc_data = self.process_document(pdf_path)
                results.append(doc_data)

            except Exception as e:
                logger.error(f"\n✗ Failed to process {pdf_path.name}: {e}")
                failed.append(pdf_path.name)
                continue

        # Summary
        logger.info(f"\n{'='*60}")
        logger.info(f"BATCH PROCESSING COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"✓ Processed: {len(results)} documents")
        logger.info(f"✗ Failed: {len(failed)} documents")

        if failed:
            logger.info(f"\nFailed documents:")
            for filename in failed:
                logger.info(f"  - {filename}")

        return results


def process_single_document(
    pdf_path: str,
    skip_figures: bool = False,
    skip_descriptions: bool = False,
    skip_upload: bool = False,
) -> dict:
    """Convenience function to process a single document."""
    pipeline = DocumentIngestionPipeline(
        skip_figures=skip_figures,
        skip_descriptions=skip_descriptions,
        skip_upload=skip_upload,
    )
    return pipeline.process_document(Path(pdf_path))


def process_all_documents(
    limit: Optional[int] = None,
    skip_figures: bool = False,
    skip_descriptions: bool = False,
    skip_upload: bool = False,
) -> List[dict]:
    """Convenience function to process all documents."""
    pipeline = DocumentIngestionPipeline(
        skip_figures=skip_figures,
        skip_descriptions=skip_descriptions,
        skip_upload=skip_upload,
    )
    return pipeline.process_all_documents(limit=limit)
