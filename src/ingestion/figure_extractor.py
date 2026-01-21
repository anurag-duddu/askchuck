"""
Figure extraction from PDFs using PyMuPDF page rendering.
Handles VECTOR GRAPHICS by rendering page regions at 300 DPI.

Based on evaluation findings: Owen's papers contain vector graphics,
not embedded images. Page rendering works for all figure types.
See .docs/PDF-EXTRACTION-EVALUATION-FINDINGS.md for details.
"""

import logging
import re
from pathlib import Path
from typing import List, Optional, Tuple

import fitz  # PyMuPDF

from src.utils.config import FIGURES_DIR

logger = logging.getLogger(__name__)


class FigureExtractor:
    """
    Extracts figures from PDF documents using page region rendering.
    Works for vector graphics, embedded images, tables, and mixed content.
    """

    # Rendering resolution
    DPI = 300  # 300 DPI for high-quality output

    # Caption detection pattern
    CAPTION_PATTERN = re.compile(
        r"(?:Figure|Fig\.?)\s+(\d+)[.:]\s*(.*?)(?=(?:Figure|Fig\.?)\s+\d+|$)",
        re.IGNORECASE | re.DOTALL,
    )

    def __init__(self):
        """Initialize figure extractor."""
        FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    def extract_figures(self, pdf_path: Path, doc_id: str) -> List[dict]:
        """
        Extract all figures from a PDF document via page rendering.

        Args:
            pdf_path: Path to the PDF file
            doc_id: Document identifier for naming figures

        Returns:
            List of figure metadata dictionaries
        """
        logger.info(f"Extracting figures from: {pdf_path.name}")

        doc = fitz.open(pdf_path)
        figures = []
        figure_num = 1

        for page_num in range(len(doc)):
            page = doc[page_num]

            # Detect figure captions on this page
            captions = self._detect_captions(page)

            for caption_text, caption_num in captions:
                try:
                    # Estimate bounding box for figure above caption
                    bbox = self._estimate_figure_bbox(page, caption_text)

                    # Render the figure region at 300 DPI
                    figure_image = self._render_region(page, bbox)

                    # Save figure
                    figure_id = f"{doc_id}_fig_{figure_num}"
                    figure_path = FIGURES_DIR / f"{figure_id}.png"
                    figure_image.save(str(figure_path))

                    # Create figure metadata
                    figure_meta = {
                        "figure_id": figure_id,
                        "figure_number": caption_num if caption_num else figure_num,
                        "page": page_num + 1,
                        "caption": caption_text.strip(),
                        "local_path": str(figure_path.relative_to(FIGURES_DIR.parent)),
                        "cloudflare_url": None,  # Populated by uploader
                        "description": None,  # Populated by describer
                        "bbox": list(bbox),
                        "width": figure_image.width,
                        "height": figure_image.height,
                    }

                    figures.append(figure_meta)
                    figure_num += 1

                    logger.info(
                        f"  Extracted Figure {caption_num}: {caption_text[:50]}..."
                    )

                except Exception as e:
                    logger.error(f"Failed to extract figure from page {page_num + 1}: {e}")
                    continue

        doc.close()
        logger.info(f"Extracted {len(figures)} figures total")
        return figures

    def _detect_captions(self, page: fitz.Page) -> List[Tuple[str, Optional[int]]]:
        """
        Detect figure captions on a page.

        Returns:
            List of (caption_text, figure_number) tuples
        """
        text = page.get_text()
        captions = []

        # Find all caption matches
        matches = self.CAPTION_PATTERN.finditer(text)

        for match in matches:
            figure_num = int(match.group(1))
            caption_text = match.group(2).strip()

            # Clean caption text (remove newlines, extra spaces)
            caption_text = " ".join(caption_text.split())

            # Limit caption length
            if len(caption_text) > 500:
                caption_text = caption_text[:500] + "..."

            captions.append((caption_text, figure_num))

        return captions

    def _estimate_figure_bbox(
        self, page: fitz.Page, caption_text: str
    ) -> Tuple[float, float, float, float]:
        """
        Estimate the bounding box of a figure based on its caption.

        Uses heuristic: Figure is typically 250 points above caption,
        full column width.

        Returns:
            (x0, y0, x1, y1) bounding box
        """
        # Search for caption text position
        text_instances = page.search_for(caption_text[:50])  # First 50 chars

        if text_instances:
            # Use first instance
            caption_rect = text_instances[0]

            # Get page dimensions
            page_width = page.rect.width
            page_height = page.rect.height

            # Heuristic: Figure is above caption
            # Typical academic layout: ~250pt figure height
            figure_height = 250

            # Estimate figure bounding box
            x0 = 72  # Left margin (1 inch)
            x1 = page_width - 72  # Right margin
            y1 = caption_rect.y0 - 10  # Just above caption
            y0 = max(72, y1 - figure_height)  # Above caption

            # For two-column layout, check caption x-position
            if caption_rect.x0 > page_width / 2:
                # Right column
                x0 = page_width / 2 + 20
                x1 = page_width - 72
            elif caption_rect.x1 < page_width / 2:
                # Left column
                x0 = 72
                x1 = page_width / 2 - 20

            return (x0, y0, x1, y1)
        else:
            # Fallback: Default to full page width, middle region
            return (72, 150, page.rect.width - 72, 450)

    def _render_region(
        self, page: fitz.Page, bbox: Tuple[float, float, float, float]
    ) -> "PIL.Image.Image":
        """
        Render a specific region of a page at 300 DPI.

        Args:
            page: PyMuPDF page object
            bbox: (x0, y0, x1, y1) bounding box

        Returns:
            PIL Image of the rendered region
        """
        # Calculate zoom factor for 300 DPI
        # PyMuPDF default is 72 DPI
        zoom = self.DPI / 72
        mat = fitz.Matrix(zoom, zoom)

        # Create clip rectangle
        clip = fitz.Rect(bbox)

        # Render page region to pixmap
        pix = page.get_pixmap(matrix=mat, clip=clip)

        # Convert to PIL Image
        from PIL import Image
        import io

        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))

        return img


def extract_figures_from_pdf(pdf_path: str, doc_id: str) -> List[dict]:
    """Convenience function to extract figures from a single PDF."""
    extractor = FigureExtractor()
    return extractor.extract_figures(Path(pdf_path), doc_id)
