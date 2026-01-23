"""
PDF parsing using PyMuPDF for structure-aware text extraction.
Handles Owen's two-column academic layout with block-level extraction.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

from src.utils.config import PROCESSED_DIR, RAW_DIR

logger = logging.getLogger(__name__)


class OwenPDFParser:
    """
    Parser for Charles Owen's academic PDFs.
    Uses PyMuPDF for text extraction with block-level sorting for reading order.
    """

    def __init__(self):
        """Initialize the PDF parser."""
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    def parse_document(self, pdf_path: Path) -> dict:
        """
        Parse a single PDF document and extract structured content.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary with document structure, metadata, and content
        """
        logger.info(f"Parsing document: {pdf_path.name}")

        # Open PDF with PyMuPDF
        doc = fitz.open(pdf_path)

        # Generate document ID from filename
        doc_id = self._generate_doc_id(pdf_path)

        # Extract metadata
        metadata = self._extract_metadata(doc, pdf_path)

        # Extract full text with reading order
        full_text = self._extract_text(doc)

        # Extract sections (simple heuristic-based approach)
        sections = self._extract_sections(doc)

        doc.close()

        return {
            "document_id": doc_id,
            "metadata": metadata,
            "sections": sections,
            "figures": [],  # Populated by figure_extractor
            "full_text": full_text,
        }

    def _generate_doc_id(self, pdf_path: Path) -> str:
        """Generate a consistent document ID from filename."""
        # Remove extension, convert to lowercase, replace spaces/hyphens
        name = pdf_path.stem.lower()
        name = name.replace(" ", "_").replace("-", "_")
        # Add author prefix for consistency
        return f"owen_{name}"

    def _extract_metadata(self, doc: fitz.Document, pdf_path: Path) -> dict:
        """Extract document metadata."""
        # Get PyMuPDF metadata
        pdf_metadata = doc.metadata

        # Extract from document
        metadata = {
            "title": self._extract_title(doc, pdf_metadata, pdf_path),
            "author": pdf_metadata.get("author", "Charles L. Owen"),
            "publication_date": self._extract_date(doc),
            "source": self._extract_source(doc),
            "filename": pdf_path.name,
            "total_pages": len(doc),
            "processed_at": datetime.utcnow().isoformat() + "Z",
        }

        return metadata

    def _extract_title(
        self, doc: fitz.Document, pdf_metadata: dict, pdf_path: Path = None
    ) -> str:
        """Extract document title."""
        # Try PDF metadata first
        pdf_title = pdf_metadata.get("title", "")

        # Check if title is valid (not a PostScript artifact like "pmu1435.out")
        if pdf_title and not self._is_invalid_title(pdf_title):
            return pdf_title

        # Fallback: Extract from first page (largest text or first line)
        page = doc[0]
        text = page.get_text()
        lines = text.split("\n")

        # Get first substantial non-empty line (skip headers like "Institute of Design")
        for line in lines:
            line = line.strip()
            if len(line) > 10 and not self._is_invalid_title(line):
                # Skip common header lines
                if "institute of design" in line.lower():
                    continue
                if "illinois institute" in line.lower():
                    continue
                return line

        # Final fallback: Use cleaned filename
        if pdf_path:
            return self._title_from_filename(pdf_path.name)

        return "Untitled Document"

    def _is_invalid_title(self, title: str) -> bool:
        """Check if a title is a technical artifact rather than a real title."""
        if not title:
            return True
        title_lower = title.lower()
        # PostScript artifacts
        if "pmu" in title_lower and ".out" in title_lower:
            return True
        if title_lower.startswith("(") and "composite" in title_lower:
            return True
        # Too short
        if len(title.strip()) < 5:
            return True
        return False

    def _title_from_filename(self, filename: str) -> str:
        """Generate a readable title from a filename."""
        # Remove extension
        name = filename.rsplit(".", 1)[0]
        # Replace separators with spaces
        name = name.replace("-", " ").replace("_", " ")
        # Title case
        return name.title()

    def _extract_date(self, doc: fitz.Document) -> Optional[str]:
        """Extract publication date if present."""
        # Look for date patterns in first 2 pages
        text = ""
        for page_num in range(min(2, len(doc))):
            text += doc[page_num].get_text()

        # Pattern for Owen's date format: "Month, Year" or "Month Year"
        date_pattern = r"(January|February|March|April|May|June|July|August|September|October|November|December),?\s+\d{4}"
        match = re.search(date_pattern, text)
        if match:
            return match.group(0)

        return None

    def _extract_source(self, doc: fitz.Document) -> Optional[str]:
        """Extract source/publication information."""
        # Look for common sources in first 3 pages
        text = ""
        for page_num in range(min(3, len(doc))):
            text += doc[page_num].get_text()

        text_lower = text.lower()

        # Look for common sources in Owen's work
        sources = [
            "Business Process Management Institute",
            "BPMInstitute.org",
            "Design Studies",
            "Design Processes Newsletter",
            "Institute of Design",
            "IIT Institute of Design",
        ]

        for source in sources:
            if source.lower() in text_lower:
                return source

        return None

    def _extract_text(self, doc: fitz.Document) -> str:
        """Extract full text with proper reading order for multi-column layouts."""
        full_text = []

        for page_num, page in enumerate(doc):
            # Get text blocks with coordinates
            blocks = page.get_text("blocks")

            # Sort blocks by (y, x) for reading order
            # This handles two-column layout by reading top-to-bottom, left-to-right
            sorted_blocks = sorted(blocks, key=lambda b: (int(b[1] / 10), b[0]))

            page_text = []
            for block in sorted_blocks:
                # block format: (x0, y0, x1, y1, "text", block_no, block_type)
                text = block[4].strip()
                if text:
                    page_text.append(text)

            if page_text:
                full_text.append(f"=== Page {page_num + 1} ===\n")
                full_text.append("\n\n".join(page_text))
                full_text.append("\n\n")

        return "".join(full_text)

    def _extract_sections(self, doc: fitz.Document) -> list:
        """
        Extract sections with simple heuristic-based approach.
        Identifies headings based on font size and formatting.
        """
        sections = []
        current_section = None

        for page_num, page in enumerate(doc):
            # Get detailed text with formatting info
            blocks = page.get_text("dict")["blocks"]

            for block in blocks:
                if "lines" not in block:
                    continue

                for line in block["lines"]:
                    # Get text and font size
                    line_text = ""
                    max_font_size = 0

                    for span in line["spans"]:
                        line_text += span["text"]
                        max_font_size = max(max_font_size, span["size"])

                    line_text = line_text.strip()
                    if not line_text:
                        continue

                    # Heuristic: Larger font = heading
                    # Average body text is ~10-11pt, headings are ~12-16pt
                    if max_font_size > 11.5 and len(line_text) < 100:
                        # Likely a heading
                        if current_section:
                            sections.append(current_section)

                        # Determine level based on font size
                        level = 1 if max_font_size > 14 else 2

                        current_section = {
                            "heading": line_text,
                            "level": level,
                            "content": "",
                            "page_start": page_num + 1,
                            "page_end": page_num + 1,
                        }
                    elif current_section:
                        # Regular content
                        current_section["content"] += line_text + " "
                        current_section["page_end"] = page_num + 1

        # Add last section
        if current_section:
            sections.append(current_section)

        # Clean up content
        for section in sections:
            section["content"] = section["content"].strip()

        return sections

    def parse_all_documents(self) -> list:
        """
        Parse all PDF documents in the raw directory.

        Returns:
            List of parsed document dictionaries
        """
        pdf_files = sorted(RAW_DIR.glob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files to process")

        results = []
        for pdf_path in pdf_files:
            try:
                doc_data = self.parse_document(pdf_path)
                results.append(doc_data)

                # Save intermediate result
                output_path = PROCESSED_DIR / f"{doc_data['document_id']}.json"
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(doc_data, f, indent=2, ensure_ascii=False)

                logger.info(f"Saved: {output_path.name}")

            except Exception as e:
                logger.error(f"Failed to parse {pdf_path.name}: {e}")
                continue

        return results


def parse_single_pdf(pdf_path: str) -> dict:
    """Convenience function to parse a single PDF."""
    parser = OwenPDFParser()
    return parser.parse_document(Path(pdf_path))


def parse_all_pdfs() -> list:
    """Convenience function to parse all PDFs."""
    parser = OwenPDFParser()
    return parser.parse_all_documents()
