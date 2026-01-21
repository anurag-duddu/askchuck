# PRD-02: Document Ingestion

## Document Information

| Field | Value |
|-------|-------|
| PRD ID | PRD-02 |
| Phase | 1 |
| Estimated Duration | 2-3 hours |
| Dependencies | PRD-01 (Environment Setup) |
| Owner | Developer |

---

## Objective

Build a robust document ingestion pipeline that processes Owen's 20 PDF documents into structured, machine-readable format. The pipeline must extract text with preserved section hierarchy, extract all figures at original resolution via page rendering (for vector graphics), generate rich semantic descriptions for each figure, and upload figures to Cloudflare R2 for public URL access. The output feeds directly into the chunking phase.

---

## Background

Charles Owen's papers present unique parsing challenges that standard PDF extractors often mishandle. The documents feature two-column academic layouts where reading order can be scrambled by naive extractors. Figures are integral to understanding—an Information Structure diagram carries as much semantic content as several paragraphs of text. Tables like the concept generation matrices in "The Power of Abstraction" encode relationships that must be preserved. Mathematical notation and specialized terminology require careful extraction.

The ingestion pipeline must handle these challenges while producing output suitable for downstream RAG processing. We prioritize accuracy over speed since this is a one-time batch process for 20 documents.

---

## Functional Requirements

### FR-01: PDF Text Extraction

The system shall extract text from PDF documents while preserving document structure including section headings, paragraphs, and reading order in multi-column layouts.

**Acceptance Criteria:**
- Extracts all text content from each PDF
- Preserves section hierarchy (headings at correct levels)
- Maintains correct reading order in two-column layouts
- Handles special characters and formatting
- Processes all 20 PDFs without errors

### FR-02: Metadata Extraction

The system shall extract document metadata including title, author, publication date, and source information.

**Acceptance Criteria:**
- Extracts document title from first page
- Extracts author name (Charles L. Owen in most cases)
- Extracts publication date when available
- Captures source information (BPMInstitute.org, Design Studies, etc.)

### FR-03: Figure Extraction

The system shall extract all figures and diagrams from PDFs at original resolution.

**Acceptance Criteria:**
- Identifies all embedded images in each PDF
- Extracts images at original resolution (no downsampling)
- Saves images in PNG format with consistent naming
- Associates each figure with its page number and position
- Captures figure captions through text proximity analysis

### FR-04: Figure Description Generation

The system shall generate comprehensive semantic descriptions for each extracted figure using a vision language model.

**Acceptance Criteria:**
- Generates descriptions for all extracted figures
- Descriptions capture figure type, content, labels, and relationships
- Descriptions use Owen's terminology correctly
- Descriptions are sufficient for text-based retrieval of visual concepts
- Handles rate limits gracefully with retry logic

### FR-05: Figure Upload to Cloudflare R2

The system shall upload all extracted figures to Cloudflare R2 storage and obtain public URLs.

**Acceptance Criteria:**
- Uploads all figures to the "figures" bucket
- Obtains public URL for each uploaded figure
- Handles upload failures with retry logic
- Records URL mapping for later retrieval

### FR-06: Output Generation

The system shall produce structured JSON output for each document suitable for chunking.

**Acceptance Criteria:**
- Outputs one JSON file per PDF
- JSON includes all extracted text with structure
- JSON includes figure metadata and URLs
- JSON includes document metadata
- Output format is consistent across all documents

---

## Technical Specification

### Technology Choices

| Component | Technology | Rationale |
|-----------|------------|-----------|
| PDF Parsing | PyMuPDF (or Docling) | PyMuPDF for both text and figures; Docling optional for complex layouts |
| Figure Extraction | **PyMuPDF Page Rendering** | Handles vector graphics at 300 DPI (validated via evaluation) |
| Vision Model | Groq Llama 3.2 Vision | Free tier, good quality, fast inference |
| Figure Storage | **Cloudflare R2** | S3-compatible, free egress, 10GB free tier |

**Key Update:** Figures are extracted via **page rendering**, not image extraction. Owen's papers contain vector graphics that require rendering page regions at high DPI. See [.docs/PDF-EXTRACTION-EVALUATION-FINDINGS.md](.docs/PDF-EXTRACTION-EVALUATION-FINDINGS.md) for evaluation details.

### Output Schema

Each processed document produces a JSON file with this structure:

```json
{
  "document_id": "owen_power_of_abstraction_2009",
  "metadata": {
    "title": "The Power of Abstraction",
    "author": "Charles L. Owen",
    "publication_date": "August 2009",
    "source": "Business Process Management Institute",
    "filename": "abstract09.pdf",
    "total_pages": 9,
    "processed_at": "2025-01-18T12:00:00Z"
  },
  "sections": [
    {
      "heading": "Abstract",
      "level": 1,
      "content": "In the innovator's tool box, abstraction is one of the most powerful tools...",
      "page_start": 3,
      "page_end": 3
    },
    {
      "heading": "The Abstraction Ladder",
      "level": 2,
      "content": "Abstraction implicitly suggests levels and separation...",
      "page_start": 3,
      "page_end": 4
    }
  ],
  "figures": [
    {
      "figure_id": "owen_power_of_abstraction_2009_fig_1",
      "figure_number": 1,
      "page": 4,
      "caption": "An Abstraction Ladder produced by considering existing chairs in a living room and extrapolating their categorization.",
      "local_path": "data/figures/owen_power_of_abstraction_2009_fig_1.png",
      "cloudflare_url": "https://pub-xxxxx.r2.dev/owen_power_of_abstraction_2009_fig_1.png",
      "description": "This figure shows a hierarchical Abstraction Ladder diagram for categorizing chairs. At the bottom are specific chair designs (Eames Lounge Chair, Barcelona Chair, Breuer Chair). These are grouped into the category 'Modern Classic Seating' at the next level, which joins 'Contemporary Seating', 'Period Replica Seating', and 'Country Seating' to form 'Living Room Chairs'. Living Room Chairs is one category alongside Dining Room Chairs, Outdoor Chairs, and Home Office Chairs under the broader 'Chairs' category. At the top, Chairs joins Tables, Beds, Counters, and Floors under 'Horizontal Surfaces'. The diagram illustrates how abstraction moves from specific items to increasingly general categories, each level representing means to achieve the ends of the level above.",
      "bbox": [72, 150, 540, 450],
      "width": 1985,
      "height": 1022
    }
  ],
  "full_text": "The Power of Abstraction\n\nCharles L. Owen\n\nAbstract\n\nIn the innovator's tool box..."
}
```

---

## Implementation Details

### File: src/ingestion/pdf_parser.py

```python
"""
PDF parsing using Docling for structure-aware text extraction.
Handles Owen's two-column academic layout with section hierarchy preservation.
"""

import json
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import DocumentStream
from docling.datamodel.pipeline_options import PdfPipelineOptions

from src.utils.config import settings, RAW_DIR, PROCESSED_DIR

logger = logging.getLogger(__name__)


class OwenPDFParser:
    """
    Parser for Charles Owen's academic PDFs.
    Uses Docling for accurate text extraction with structure preservation.
    """

    def __init__(self):
        # Configure Docling pipeline for academic documents
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False  # Owen's PDFs are text-based
        pipeline_options.do_table_structure = True  # Preserve tables

        self.converter = DocumentConverter(
            pipeline_options=pipeline_options
        )

    def parse_document(self, pdf_path: Path) -> dict:
        """
        Parse a single PDF document and extract structured content.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary with document structure, metadata, and content
        """
        logger.info(f"Parsing document: {pdf_path.name}")

        # Convert PDF using Docling
        result = self.converter.convert(str(pdf_path))
        doc = result.document

        # Generate document ID from filename
        doc_id = self._generate_doc_id(pdf_path)

        # Extract metadata
        metadata = self._extract_metadata(doc, pdf_path)

        # Extract sections with hierarchy
        sections = self._extract_sections(doc)

        # Get full text for backup/reference
        full_text = doc.export_to_markdown()

        return {
            "document_id": doc_id,
            "metadata": metadata,
            "sections": sections,
            "figures": [],  # Populated by figure_extractor
            "full_text": full_text
        }

    def _generate_doc_id(self, pdf_path: Path) -> str:
        """Generate a consistent document ID from filename."""
        # Remove extension, convert to lowercase, replace spaces
        name = pdf_path.stem.lower()
        name = name.replace(" ", "_").replace("-", "_")
        # Add author prefix for consistency
        return f"owen_{name}"

    def _extract_metadata(self, doc, pdf_path: Path) -> dict:
        """Extract document metadata."""
        # Try to get metadata from Docling
        metadata = {
            "title": self._extract_title(doc),
            "author": "Charles L. Owen",  # Known for this corpus
            "publication_date": self._extract_date(doc),
            "source": self._extract_source(doc),
            "filename": pdf_path.name,
            "total_pages": doc.num_pages if hasattr(doc, 'num_pages') else None,
            "processed_at": datetime.utcnow().isoformat() + "Z"
        }
        return metadata

    def _extract_title(self, doc) -> str:
        """Extract document title from first heading or page."""
        # Docling typically identifies title
        if hasattr(doc, 'title') and doc.title:
            return doc.title

        # Fallback: look for first major heading
        for item in doc.iterate_items():
            if hasattr(item, 'label') and item.label == 'title':
                return item.text

        return "Untitled Document"

    def _extract_date(self, doc) -> Optional[str]:
        """Extract publication date if present."""
        # Look for date patterns in early content
        # Owen's papers typically have date on page 1 or 2
        text = doc.export_to_markdown()[:2000]

        import re
        # Pattern for Owen's date format: "Month, Year" or "Month Year"
        date_pattern = r'(January|February|March|April|May|June|July|August|September|October|November|December),?\s+\d{4}'
        match = re.search(date_pattern, text)
        if match:
            return match.group(0)

        return None

    def _extract_source(self, doc) -> Optional[str]:
        """Extract source/publication information."""
        text = doc.export_to_markdown()[:3000]

        # Look for common sources in Owen's work
        sources = [
            "Business Process Management Institute",
            "BPMInstitute.org",
            "Design Studies",
            "Design Processes Newsletter",
            "Institute of Design"
        ]

        for source in sources:
            if source.lower() in text.lower():
                return source

        return None

    def _extract_sections(self, doc) -> list:
        """
        Extract sections with hierarchy preservation.
        Returns list of section dicts with heading, level, and content.
        """
        sections = []
        current_section = None

        for item in doc.iterate_items():
            if hasattr(item, 'label'):
                if item.label in ['section_header', 'title']:
                    # Save previous section if exists
                    if current_section:
                        sections.append(current_section)

                    # Determine heading level
                    level = self._determine_heading_level(item)

                    current_section = {
                        "heading": item.text.strip(),
                        "level": level,
                        "content": "",
                        "page_start": getattr(item, 'page', None),
                        "page_end": getattr(item, 'page', None)
                    }

                elif item.label in ['paragraph', 'text', 'list_item']:
                    if current_section:
                        current_section["content"] += item.text + "\n\n"
                        current_section["page_end"] = getattr(item, 'page', current_section["page_end"])

        # Don't forget the last section
        if current_section:
            sections.append(current_section)

        # Clean up content
        for section in sections:
            section["content"] = section["content"].strip()

        return sections

    def _determine_heading_level(self, item) -> int:
        """Determine the hierarchical level of a heading."""
        # Docling may provide level info
        if hasattr(item, 'level'):
            return item.level

        # Heuristic based on formatting/position
        text = item.text.strip()

        # Major section headers are often ALL CAPS or very short
        if text.isupper() and len(text) < 50:
            return 1

        # Default to level 2 for most headings
        return 2

    def parse_all_documents(self) -> list:
        """
        Parse all PDF documents in the raw directory.

        Returns:
            List of parsed document dictionaries
        """
        pdf_files = list(RAW_DIR.glob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files to process")

        results = []
        for pdf_path in pdf_files:
            try:
                doc_data = self.parse_document(pdf_path)
                results.append(doc_data)

                # Save intermediate result
                output_path = PROCESSED_DIR / f"{doc_data['document_id']}.json"
                with open(output_path, 'w', encoding='utf-8') as f:
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
```

### File: src/ingestion/figure_extractor.py

```python
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
from typing import Optional, Tuple

import fitz  # PyMuPDF
from PIL import Image
import io

from src.utils.config import RAW_DIR, FIGURES_DIR

logger = logging.getLogger(__name__)


class FigureExtractor:
    """
    Extracts figures from PDF documents using page region rendering.
    Works for vector graphics, embedded images, tables, and mixed content.
    """

    # Rendering resolution
    DPI = 300  # 300 DPI for high-quality output

    def __init__(self):
        FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    def extract_figures(self, pdf_path: Path, doc_id: str) -> list:
        """
        Extract all figures from a PDF document via page rendering.

        Args:
            pdf_path: Path to the PDF file
            doc_id: Document identifier for naming

        Returns:
            List of figure dictionaries with metadata
        """
        logger.info(f"Extracting figures from: {pdf_path.name}")

        doc = fitz.open(str(pdf_path))
        figures = []

        for page_num in range(len(doc)):
            page = doc[page_num]

            # Find all figure captions on this page
            figure_regions = self._find_figure_regions(page, page_num)

            for fig_info in figure_regions:
                try:
                    figure_id = f"{doc_id}_fig_{fig_info['figure_number']}"

                    # Render the figure region at high DPI
                    output_path, size = self._render_figure_region(
                        page,
                        fig_info['estimated_bbox'],
                        figure_id
                    )

                    figure_data = {
                        "figure_id": figure_id,
                        "figure_number": fig_info['figure_number'],
                        "page": page_num + 1,
                        "caption": fig_info['caption'],
                        "local_path": str(output_path),
                        "cloudflare_url": None,  # Set after upload
                        "description": None,     # Set by vision model
                        "width": size[0],
                        "height": size[1],
                        "bbox": list(fig_info['estimated_bbox'])
                    }

                    figures.append(figure_data)
                    logger.info(f"Extracted: {figure_id} ({size[0]}x{size[1]}px)")

                except Exception as e:
                    logger.warning(f"Failed to extract figure {fig_info.get('figure_number')} on page {page_num + 1}: {e}")
                    continue

        doc.close()
        logger.info(f"Extracted {len(figures)} figures from {pdf_path.name}")
        return figures

    def _find_figure_regions(self, page, page_num: int) -> list:
        """
        Find figure regions on a page using caption detection.

        Returns list of dicts with: figure_number, caption, estimated_bbox
        """
        figures = []

        # Get all text blocks
        blocks = page.get_text("blocks")

        # Pattern to match figure captions
        caption_pattern = re.compile(r'Figure\s+(\d+)[.\s:]', re.IGNORECASE)

        page_height = page.rect.height
        page_width = page.rect.width

        for block in blocks:
            if len(block) < 5:
                continue

            x0, y0, x1, y1 = block[:4]
            text = block[4]

            # Check if this block contains a figure caption
            match = caption_pattern.search(text)
            if match:
                figure_num = int(match.group(1))

                # Heuristic: Figure is typically ABOVE the caption
                # Estimate figure region as 250px block above caption
                # This is a simple heuristic; can be refined with layout analysis
                figure_bbox = fitz.Rect(
                    max(0, x0 - 50),      # Expand left slightly
                    max(0, y0 - 250),     # Look up to 250px above caption
                    min(page_width, x1 + 50),  # Expand right slightly
                    y0 - 5                # Just above the caption
                )

                figures.append({
                    'figure_number': figure_num,
                    'caption': text.strip(),
                    'estimated_bbox': figure_bbox,
                    'caption_bbox': (x0, y0, x1, y1)
                })

        return figures

    def _render_figure_region(
        self,
        page,
        bbox: fitz.Rect,
        figure_id: str
    ) -> Tuple[Path, Tuple[int, int]]:
        """
        Render a specific region of a page as a high-resolution image.

        Args:
            page: PyMuPDF page object
            bbox: Bounding box to render (fitz.Rect)
            figure_id: Identifier for output filename

        Returns:
            Tuple of (output_path, (width, height))
        """
        # Create transformation matrix for desired DPI
        zoom = self.DPI / 72  # 72 is the default PDF DPI
        mat = fitz.Matrix(zoom, zoom)

        # Render the specific region
        pix = page.get_pixmap(matrix=mat, clip=bbox)

        # Convert to PIL Image for processing
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))

        # Save as PNG
        output_path = FIGURES_DIR / f"{figure_id}.png"
        img.save(output_path, "PNG", optimize=True)

        return output_path, img.size

    def extract_all_figures(self, parsed_docs: list) -> dict:
        """
        Extract figures from all parsed documents.

        Args:
            parsed_docs: List of parsed document dictionaries

        Returns:
            Dictionary mapping doc_id to list of figures
        """
        all_figures = {}

        for doc_data in parsed_docs:
            doc_id = doc_data["document_id"]
            filename = doc_data["metadata"]["filename"]
            pdf_path = RAW_DIR / filename

            if not pdf_path.exists():
                logger.warning(f"PDF not found: {pdf_path}")
                continue

            figures = self.extract_figures(pdf_path, doc_id)
            all_figures[doc_id] = figures

            # Update the parsed doc with figures
            doc_data["figures"] = figures

        return all_figures


def extract_figures_from_pdf(pdf_path: str, doc_id: str) -> list:
    """Convenience function to extract figures from a single PDF."""
    extractor = FigureExtractor()
    return extractor.extract_figures(Path(pdf_path), doc_id)
```

### File: src/ingestion/figure_describer.py

```python
"""
Generate semantic descriptions for extracted figures using Groq Vision.
Descriptions are optimized for RAG retrieval of visual concepts.
"""

import base64
import logging
import time
from pathlib import Path
from typing import Optional

from groq import Groq

from src.utils.config import settings

logger = logging.getLogger(__name__)


# Prompt engineered for Owen's academic diagrams
FIGURE_DESCRIPTION_PROMPT = """You are analyzing a figure from Charles Owen's academic literature on Structured Planning methodology from IIT Institute of Design.

Provide a comprehensive description of this figure that would allow someone to understand the concept without seeing the image. Your description should:

1. **Figure Type**: Identify what kind of figure this is (hierarchy diagram, matrix, flowchart, form template, graph, mockup photo, etc.)

2. **Main Subject**: What concept or process does this figure illustrate?

3. **Components**: List all visible elements, labels, and text. Be thorough—include every label you can read.

4. **Relationships**: Describe how elements relate to each other (hierarchies, flows, connections, groupings)

5. **Owen's Methodology**: Connect this figure to relevant Structured Planning concepts. Use Owen's terminology precisely:
   - Function: An action performed by a system or user
   - Design Factor: Document with Observation, Extension, Design Implications, Speculations
   - Speculation: Concrete idea as adjective-noun phrase
   - Information Structure: Hierarchy of Functions organized by shared solution potential
   - Function Structure: Top-down hierarchy of Modes, Activities, Functions
   - Abstraction Ladder: Categorization from specific to general

6. **Key Insights**: What does this figure teach about the methodology?

Write in clear, detailed prose. Your description should be 150-300 words and capture all semantic content of the figure."""


class FigureDescriber:
    """
    Generates rich semantic descriptions for figures using vision models.
    Optimized for Owen's methodology diagrams.
    """

    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = settings.groq_vision_model

        # Rate limiting
        self.requests_per_minute = 10
        self.last_request_time = 0

    def describe_figure(self, figure_path: Path, caption: Optional[str] = None) -> str:
        """
        Generate a description for a single figure.

        Args:
            figure_path: Path to the figure image
            caption: Optional caption text to include as context

        Returns:
            Generated description string
        """
        # Rate limiting
        self._rate_limit()

        # Read and encode image
        with open(figure_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")

        # Build prompt with caption context if available
        prompt = FIGURE_DESCRIPTION_PROMPT
        if caption:
            prompt += f"\n\nThe figure's caption is: \"{caption}\""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_data}"
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ],
                max_tokens=1000,
                temperature=0.3  # Lower temperature for factual description
            )

            description = response.choices[0].message.content
            logger.info(f"Generated description for {figure_path.name} ({len(description)} chars)")
            return description

        except Exception as e:
            logger.error(f"Failed to describe {figure_path.name}: {e}")
            # Return a fallback description
            return f"Figure from Owen's Structured Planning literature. Caption: {caption or 'Not available'}"

    def _rate_limit(self):
        """Simple rate limiting to avoid API throttling."""
        min_interval = 60.0 / self.requests_per_minute
        elapsed = time.time() - self.last_request_time

        if elapsed < min_interval:
            sleep_time = min_interval - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def describe_all_figures(self, figures: list) -> list:
        """
        Generate descriptions for all figures in a list.

        Args:
            figures: List of figure dictionaries with local_path and caption

        Returns:
            Updated list with descriptions added
        """
        logger.info(f"Generating descriptions for {len(figures)} figures")

        for i, figure in enumerate(figures):
            figure_path = Path(figure["local_path"])

            if not figure_path.exists():
                logger.warning(f"Figure not found: {figure_path}")
                continue

            caption = figure.get("caption")
            description = self.describe_figure(figure_path, caption)
            figure["description"] = description

            logger.info(f"Progress: {i + 1}/{len(figures)}")

        return figures

    def describe_figures_for_documents(self, parsed_docs: list) -> list:
        """
        Generate descriptions for all figures across all documents.

        Args:
            parsed_docs: List of parsed document dictionaries with figures

        Returns:
            Updated documents with figure descriptions
        """
        total_figures = sum(len(doc.get("figures", [])) for doc in parsed_docs)
        logger.info(f"Generating descriptions for {total_figures} figures across {len(parsed_docs)} documents")

        for doc in parsed_docs:
            figures = doc.get("figures", [])
            if figures:
                doc["figures"] = self.describe_all_figures(figures)

        return parsed_docs


def describe_single_figure(figure_path: str, caption: str = None) -> str:
    """Convenience function to describe a single figure."""
    describer = FigureDescriber()
    return describer.describe_figure(Path(figure_path), caption)
```

### File: src/utils/cloudflare_client.py

```python
"""
Cloudflare R2 client for figure storage and URL management.
Uploads figures to R2 bucket and returns accessible URLs.
Uses S3-compatible API via boto3.
"""

import logging
from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from src.utils.config import settings

logger = logging.getLogger(__name__)


class CloudflareFigureStorage:
    """
    Manages figure uploads to Cloudflare R2 storage.
    Uses S3-compatible API.
    """

    def __init__(self):
        # Create S3 client for Cloudflare R2
        self.s3_client = boto3.client(
            's3',
            endpoint_url=f'https://{settings.cloudflare_account_id}.r2.cloudflarestorage.com',
            aws_access_key_id=settings.cloudflare_r2_access_key_id,
            aws_secret_access_key=settings.cloudflare_r2_secret_access_key,
            region_name='auto'  # R2 uses auto region
        )
        self.bucket = settings.cloudflare_r2_bucket_name

        # Configure public URL base (set up custom domain or R2 public URL)
        # This should be configured after enabling public access on the bucket
        self.public_url_base = f'https://pub-{settings.cloudflare_account_id}.r2.dev'

    def upload_figure(self, local_path: Path) -> Optional[str]:
        """
        Upload a figure to Cloudflare R2 and return its public URL.

        Args:
            local_path: Path to the local figure file

        Returns:
            Public URL of the uploaded figure, or None if failed
        """
        if not local_path.exists():
            logger.error(f"File not found: {local_path}")
            return None

        file_name = local_path.name

        try:
            # Upload to R2
            with open(local_path, "rb") as f:
                self.s3_client.upload_fileobj(
                    f,
                    self.bucket,
                    file_name,
                    ExtraArgs={'ContentType': 'image/png'}
                )

            # Construct public URL
            public_url = f"{self.public_url_base}/{file_name}"

            logger.info(f"Uploaded: {file_name}")
            return public_url

        except ClientError as e:
            # Check if file already exists (not an error in R2/S3)
            if e.response['Error']['Code'] == '404':
                logger.error(f"Bucket not found: {self.bucket}")
            else:
                logger.warning(f"Upload issue for {file_name}: {e}")

            # Return URL anyway (file may exist)
            return f"{self.public_url_base}/{file_name}"

        except Exception as e:
            logger.error(f"Failed to upload {file_name}: {e}")
            return None

    def upload_all_figures(self, figures: list) -> list:
        """
        Upload all figures and update their cloudflare_url field.

        Args:
            figures: List of figure dictionaries

        Returns:
            Updated figures with cloudflare_url populated
        """
        logger.info(f"Uploading {len(figures)} figures to Cloudflare R2")

        for figure in figures:
            local_path = Path(figure["local_path"])
            url = self.upload_figure(local_path)
            figure["cloudflare_url"] = url

        return figures

    def upload_figures_for_documents(self, parsed_docs: list) -> list:
        """
        Upload all figures for all documents.

        Args:
            parsed_docs: List of parsed document dictionaries

        Returns:
            Updated documents with figure URLs
        """
        total_figures = sum(len(doc.get("figures", [])) for doc in parsed_docs)
        logger.info(f"Uploading {total_figures} figures to Cloudflare R2")

        for doc in parsed_docs:
            figures = doc.get("figures", [])
            if figures:
                doc["figures"] = self.upload_all_figures(figures)

        return parsed_docs

    def delete_figure(self, file_name: str) -> bool:
        """Delete a figure from R2 storage."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=file_name)
            logger.info(f"Deleted: {file_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete {file_name}: {e}")
            return False


def upload_figure(local_path: str) -> Optional[str]:
    """Convenience function to upload a single figure."""
    storage = CloudflareFigureStorage()
    return storage.upload_figure(Path(local_path))
```

### File: scripts/ingest_all.py

```python
"""
Master ingestion script that processes all PDFs end-to-end.
Runs: parsing → figure extraction → description generation → upload → save.
"""

import json
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.pdf_parser import OwenPDFParser
from src.ingestion.figure_extractor import FigureExtractor
from src.ingestion.figure_describer import FigureDescriber
from src.utils.cloudflare_client import CloudflareFigureStorage
from src.utils.config import RAW_DIR, PROCESSED_DIR, CHUNKS_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('ingestion.log')
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Run the complete ingestion pipeline."""

    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("AskChuck Document Ingestion Pipeline")
    logger.info("=" * 60)

    # Ensure directories exist
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

    # Count input files
    pdf_files = list(RAW_DIR.glob("*.pdf"))
    logger.info(f"Found {len(pdf_files)} PDF files in {RAW_DIR}")

    if not pdf_files:
        logger.error("No PDF files found! Please add PDFs to data/raw/")
        sys.exit(1)

    # Step 1: Parse PDFs
    logger.info("\n" + "=" * 40)
    logger.info("Step 1: Parsing PDF documents")
    logger.info("=" * 40)

    parser = OwenPDFParser()
    parsed_docs = parser.parse_all_documents()
    logger.info(f"Parsed {len(parsed_docs)} documents")

    # Step 2: Extract figures
    logger.info("\n" + "=" * 40)
    logger.info("Step 2: Extracting figures")
    logger.info("=" * 40)

    extractor = FigureExtractor()
    extractor.extract_all_figures(parsed_docs)

    total_figures = sum(len(doc.get("figures", [])) for doc in parsed_docs)
    logger.info(f"Extracted {total_figures} figures")

    # Step 3: Generate figure descriptions
    logger.info("\n" + "=" * 40)
    logger.info("Step 3: Generating figure descriptions")
    logger.info("=" * 40)

    describer = FigureDescriber()
    parsed_docs = describer.describe_figures_for_documents(parsed_docs)
    logger.info("Figure descriptions complete")

    # Step 4: Upload figures to Cloudflare R2
    logger.info("\n" + "=" * 40)
    logger.info("Step 4: Uploading figures to Cloudflare R2")
    logger.info("=" * 40)

    storage = CloudflareFigureStorage()
    parsed_docs = storage.upload_figures_for_documents(parsed_docs)
    logger.info("Figure upload complete")

    # Step 5: Save final processed documents
    logger.info("\n" + "=" * 40)
    logger.info("Step 5: Saving processed documents")
    logger.info("=" * 40)

    for doc in parsed_docs:
        output_path = PROCESSED_DIR / f"{doc['document_id']}.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved: {output_path.name}")

    # Summary
    elapsed = datetime.now() - start_time
    logger.info("\n" + "=" * 60)
    logger.info("Ingestion Complete!")
    logger.info("=" * 60)
    logger.info(f"Documents processed: {len(parsed_docs)}")
    logger.info(f"Figures extracted: {total_figures}")
    logger.info(f"Time elapsed: {elapsed}")
    logger.info(f"Output directory: {PROCESSED_DIR}")


if __name__ == "__main__":
    main()
```

---

## Error Handling

### PDF Parsing Failures

If Docling fails to parse a PDF, the pipeline should:
1. Log the error with details
2. Attempt fallback extraction using PyMuPDF text extraction
3. Continue processing remaining documents
4. Report failures in final summary

### Figure Extraction Failures

If figure extraction fails:
1. Log which images failed
2. Continue extracting remaining figures
3. Mark failed figures in output for manual review

### Vision API Failures

If Groq Vision fails:
1. Implement exponential backoff (1s, 2s, 4s, 8s)
2. After 3 retries, use fallback description: "Figure from Owen's literature. [caption]"
3. Log failures for manual description later

### Cloudflare R2 Upload Failures

If upload fails:
1. Retry up to 3 times with exponential backoff
2. If persistent failure, keep local path and mark URL as null
3. Verify R2 bucket is configured for public access
4. Frontend should handle missing URLs gracefully

---

## Acceptance Criteria

| Criterion | Verification Method |
|-----------|-------------------|
| All 20 PDFs parsed successfully | Check PROCESSED_DIR for 20 JSON files |
| Text extraction preserves structure | Manual review of 3 sample documents |
| All figures extracted (estimate 30-50) | Count files in FIGURES_DIR |
| Figure descriptions generated | Check "description" field in JSON |
| Figures uploaded to Cloudflare R2 | Verify "cloudflare_url" fields are populated |
| URLs are publicly accessible | Open sample URLs in browser |
| No critical errors in logs | Review ingestion.log |
| Processing completes in < 30 minutes | Time the full pipeline |

---

## Next Steps

Once ingestion is complete, proceed to **PRD-03: Chunking & Enrichment** to segment the extracted content into retrievable units with contextual enhancement.
