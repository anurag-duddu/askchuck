"""
Figure chunk generation.
Creates dedicated retrievable chunks for figures with captions and descriptions.
"""

import logging
from typing import List

from src.utils.owen_glossary import tag_chunk_with_terms

logger = logging.getLogger(__name__)


class FigureChunker:
    """
    Creates standalone chunks for figures.
    Each figure becomes a retrievable chunk with caption + description.
    """

    def create_figure_chunks(self, doc_data: dict) -> List[dict]:
        """
        Create figure chunks from document data.

        Args:
            doc_data: Processed document data with figures

        Returns:
            List of figure chunk dictionaries
        """
        doc_id = doc_data["document_id"]
        figures = doc_data.get("figures", [])

        if not figures:
            logger.info(f"  No figures in {doc_id}")
            return []

        logger.info(f"  Creating {len(figures)} figure chunks")

        figure_chunks = []

        for figure in figures:
            chunk = self._create_figure_chunk(figure, doc_data)
            figure_chunks.append(chunk)

        return figure_chunks

    def _create_figure_chunk(self, figure: dict, doc_data: dict) -> dict:
        """
        Create a single figure chunk.

        Args:
            figure: Figure metadata from ingestion
            doc_data: Document metadata

        Returns:
            Figure chunk dictionary
        """
        # Combine caption and description for text content
        caption = figure.get("caption", "")
        description = figure.get("description", "")

        # Figure text = caption + description
        figure_text = f"Figure {figure.get('figure_number', '')}: {caption}\n\n{description}"

        # Extract Owen terms from figure content
        owen_terms = tag_chunk_with_terms(figure_text)

        # Create chunk
        chunk = {
            "chunk_id": figure["figure_id"],
            "document_id": doc_data["document_id"],
            "chunk_position": -1,  # Figures don't have linear position
            "level": "figure",  # Special level for figures
            "text": figure_text,
            "enriched_text": None,  # Could be enriched if desired
            "metadata": {
                "document_title": doc_data["metadata"]["title"],
                "document_author": doc_data["metadata"]["author"],
                "chunk_type": "figure",
                "figure_number": figure.get("figure_number"),
                "figure_page": figure.get("page"),
                "figure_caption": caption,
                "figure_description": description,
                "figure_url": figure.get("cloudflare_url")
                or figure.get("local_path"),
                "owen_terms": owen_terms,
                "char_count": len(figure_text),
                "approx_tokens": len(figure_text) // 4,
                # Hierarchical metadata (figures don't have parents/children)
                "parent_id": None,
                "child_ids": [],
                # Figure-specific metadata
                "width": figure.get("width"),
                "height": figure.get("height"),
                "bbox": figure.get("bbox"),
            },
        }

        return chunk


def create_figure_chunks(doc_data: dict) -> List[dict]:
    """Convenience function to create figure chunks from document."""
    chunker = FigureChunker()
    return chunker.create_figure_chunks(doc_data)
