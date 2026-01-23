"""
Main chunking pipeline.
Orchestrates semantic chunking, figure chunking, and contextual enrichment.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from tqdm import tqdm

from src.chunking.contextual_enricher import ContextualEnricher
from src.chunking.figure_chunker import FigureChunker
from src.chunking.semantic_chunker import SemanticChunker
from src.utils.config import CHUNKS_DIR, PROCESSED_DIR

logger = logging.getLogger(__name__)


class ChunkingPipeline:
    """
    Complete chunking pipeline for processed documents.
    Combines semantic chunking, figure chunking, and contextual enrichment.
    """

    def __init__(
        self,
        skip_enrichment: bool = False,
        skip_figures: bool = False,
    ):
        """
        Initialize the chunking pipeline.

        Args:
            skip_enrichment: Skip contextual enrichment (faster)
            skip_figures: Skip figure chunk creation
        """
        self.semantic_chunker = SemanticChunker()
        self.figure_chunker = FigureChunker() if not skip_figures else None
        self.contextual_enricher = ContextualEnricher() if not skip_enrichment else None

        self.skip_enrichment = skip_enrichment
        self.skip_figures = skip_figures

        logger.info("Chunking pipeline initialized")
        logger.info(f"  Enrichment: {'disabled' if skip_enrichment else 'enabled'}")
        logger.info(f"  Figures: {'disabled' if skip_figures else 'enabled'}")

    def process_document(self, doc_path: Path) -> List[dict]:
        """
        Process a single document through the chunking pipeline.

        Args:
            doc_path: Path to processed document JSON

        Returns:
            List of all chunks (text + figure)
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Chunking: {doc_path.name}")
        logger.info(f"{'='*60}")

        # Load processed document
        with open(doc_path, "r", encoding="utf-8") as f:
            doc_data = json.load(f)

        doc_id = doc_data["document_id"]

        # Step 1: Semantic chunking
        logger.info("Step 1/4: Semantic chunking...")
        text_chunks = self.semantic_chunker.chunk_document(doc_data)
        logger.info(f"  Created {len(text_chunks)} text chunks")

        # Step 2: Figure chunking
        if not self.skip_figures and doc_data.get("figures"):
            logger.info("Step 2/4: Figure chunking...")
            figure_chunks = self.figure_chunker.create_figure_chunks(doc_data)
            logger.info(f"  Created {len(figure_chunks)} figure chunks")
        else:
            logger.info("Step 2/4: Skipping figure chunks")
            figure_chunks = []

        # Combine all chunks
        all_chunks = text_chunks + figure_chunks

        # Step 3: Contextual enrichment
        if not self.skip_enrichment:
            logger.info("Step 3/4: Contextual enrichment...")
            all_chunks = self.contextual_enricher.enrich_chunks_batch(all_chunks)
            logger.info(f"  Enriched {len(all_chunks)} chunks")
        else:
            logger.info("Step 3/4: Skipping enrichment")
            # Set enriched_text to text for all chunks
            for chunk in all_chunks:
                chunk["enriched_text"] = chunk["text"]

        # Step 4: Save output
        logger.info("Step 4/4: Saving output...")
        output_path = CHUNKS_DIR / f"{doc_id}_chunks.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_chunks, f, indent=2, ensure_ascii=False)

        logger.info(f"✓ Saved: {output_path.name}")
        logger.info(f"  Total chunks: {len(all_chunks)}")
        logger.info(f"  Text chunks: {len(text_chunks)} (parents + children)")
        logger.info(f"  Figure chunks: {len(figure_chunks)}")

        return all_chunks

    def process_all_documents(
        self, limit: Optional[int] = None
    ) -> Dict[str, List[dict]]:
        """
        Process all documents through chunking pipeline.

        Args:
            limit: Maximum number of documents to process

        Returns:
            Dictionary mapping document_id to chunks
        """
        json_files = sorted(PROCESSED_DIR.glob("*.json"))

        if limit:
            json_files = json_files[:limit]

        logger.info(f"\n{'='*60}")
        logger.info(f"STARTING BATCH CHUNKING")
        logger.info(f"{'='*60}")
        logger.info(f"Processing {len(json_files)} documents")

        results = {}
        failed = []

        # Process with progress bar
        for doc_path in tqdm(json_files, desc="Chunking documents", unit="doc"):
            try:
                chunks = self.process_document(doc_path)

                doc_id = json.loads(doc_path.read_text())["document_id"]
                results[doc_id] = chunks

            except Exception as e:
                logger.error(f"\n✗ Failed to chunk {doc_path.name}: {e}")
                failed.append(doc_path.name)
                continue

        # Summary
        logger.info(f"\n{'='*60}")
        logger.info(f"BATCH CHUNKING COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"✓ Processed: {len(results)} documents")
        logger.info(f"✗ Failed: {len(failed)} documents")

        if failed:
            logger.info(f"\nFailed documents:")
            for filename in failed:
                logger.info(f"  - {filename}")

        # Statistics
        total_chunks = sum(len(chunks) for chunks in results.values())
        logger.info(f"\nTotal chunks created: {total_chunks}")

        return results


def process_document(
    doc_path: str,
    skip_enrichment: bool = False,
    skip_figures: bool = False,
) -> List[dict]:
    """Convenience function to process a single document."""
    pipeline = ChunkingPipeline(
        skip_enrichment=skip_enrichment,
        skip_figures=skip_figures,
    )
    return pipeline.process_document(Path(doc_path))


def process_all_documents(
    limit: Optional[int] = None,
    skip_enrichment: bool = False,
    skip_figures: bool = False,
) -> Dict[str, List[dict]]:
    """Convenience function to process all documents."""
    pipeline = ChunkingPipeline(
        skip_enrichment=skip_enrichment,
        skip_figures=skip_figures,
    )
    return pipeline.process_all_documents(limit=limit)
