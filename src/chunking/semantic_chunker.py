"""
Semantic chunking with hierarchical parent-child relationships.
Uses Owen-specific separators and creates both parent and child chunks.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.utils.config import CHUNKS_DIR, PROCESSED_DIR
from src.utils.owen_glossary import tag_chunk_with_terms

logger = logging.getLogger(__name__)


class SemanticChunker:
    """
    Hierarchical semantic chunker for Owen's papers.
    Creates parent chunks (2048 tokens) and child chunks (512 tokens)
    with semantic boundaries.
    """

    # Owen-specific separators in priority order
    SEPARATORS = [
        "\n\n## ",  # Section headers
        "\n\n### ",  # Subsection headers
        "\n\n",  # Paragraph breaks
        "\n",  # Line breaks
        ". ",  # Sentence endings
        " ",  # Word breaks
    ]

    # Chunk size targets (in tokens, approximate as 4 chars/token)
    PARENT_CHUNK_SIZE = 2048 * 4  # ~8000 chars
    PARENT_CHUNK_OVERLAP = 200 * 4  # ~800 chars

    CHILD_CHUNK_SIZE = 512 * 4  # ~2000 chars
    CHILD_CHUNK_OVERLAP = 50 * 4  # ~200 chars

    def __init__(self):
        """Initialize the semantic chunker."""
        # Parent chunker
        self.parent_splitter = RecursiveCharacterTextSplitter(
            separators=self.SEPARATORS,
            chunk_size=self.PARENT_CHUNK_SIZE,
            chunk_overlap=self.PARENT_CHUNK_OVERLAP,
            length_function=len,
        )

        # Child chunker
        self.child_splitter = RecursiveCharacterTextSplitter(
            separators=self.SEPARATORS,
            chunk_size=self.CHILD_CHUNK_SIZE,
            chunk_overlap=self.CHILD_CHUNK_OVERLAP,
            length_function=len,
        )

        CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

    def chunk_document(self, doc_data: dict) -> List[dict]:
        """
        Chunk a processed document into hierarchical chunks.

        Args:
            doc_data: Processed document data from ingestion phase

        Returns:
            List of chunk dictionaries with metadata
        """
        doc_id = doc_data["document_id"]
        logger.info(f"Chunking document: {doc_id}")

        # Get full text
        full_text = doc_data.get("full_text", "")
        if not full_text:
            # Fallback: concatenate sections
            full_text = "\n\n".join(
                section["content"] for section in doc_data.get("sections", [])
            )

        # Create parent chunks
        parent_texts = self.parent_splitter.split_text(full_text)
        logger.info(f"  Created {len(parent_texts)} parent chunks")

        all_chunks = []
        chunk_position = 0

        # Process each parent chunk
        for parent_idx, parent_text in enumerate(parent_texts):
            # Create parent chunk
            parent_id = f"{doc_id}_p{parent_idx}"

            # Create child chunks from this parent
            child_texts = self.child_splitter.split_text(parent_text)
            child_ids = []

            # Create child chunk objects
            for child_idx, child_text in enumerate(child_texts):
                child_id = f"{parent_id}_c{child_idx}"
                child_ids.append(child_id)

                child_chunk = self._create_chunk(
                    chunk_id=child_id,
                    text=child_text,
                    doc_data=doc_data,
                    chunk_position=chunk_position,
                    level="child",
                    parent_id=parent_id,
                )

                all_chunks.append(child_chunk)
                chunk_position += 1

            # Create parent chunk object
            parent_chunk = self._create_chunk(
                chunk_id=parent_id,
                text=parent_text,
                doc_data=doc_data,
                chunk_position=chunk_position,
                level="parent",
                child_ids=child_ids,
            )

            all_chunks.append(parent_chunk)
            chunk_position += 1

        logger.info(f"  Total chunks created: {len(all_chunks)}")
        return all_chunks

    def _create_chunk(
        self,
        chunk_id: str,
        text: str,
        doc_data: dict,
        chunk_position: int,
        level: str,
        parent_id: Optional[str] = None,
        child_ids: Optional[List[str]] = None,
    ) -> dict:
        """
        Create a chunk dictionary with metadata.

        Args:
            chunk_id: Unique chunk identifier
            text: Chunk text content
            doc_data: Document metadata
            chunk_position: Position in document
            level: 'parent' or 'child'
            parent_id: Parent chunk ID (for children)
            child_ids: List of child IDs (for parents)

        Returns:
            Chunk dictionary
        """
        # Extract Owen terms
        owen_terms = tag_chunk_with_terms(text)

        # Determine source section and page
        source_section, page_start = self._determine_section_and_page(text, doc_data)

        # Get PDF filename from document metadata
        pdf_filename = doc_data.get("metadata", {}).get("filename", "")

        # Create chunk
        chunk = {
            "chunk_id": chunk_id,
            "document_id": doc_data["document_id"],
            "chunk_position": chunk_position,
            "level": level,
            "text": text,
            "enriched_text": None,  # Populated by enricher
            "metadata": {
                "document_title": doc_data["metadata"]["title"],
                "document_author": doc_data["metadata"]["author"],
                "source_section": source_section,
                "page_start": page_start,  # Page number for navigation
                "pdf_filename": pdf_filename,  # PDF filename for URL construction
                "owen_terms": owen_terms,
                "char_count": len(text),
                "approx_tokens": len(text) // 4,  # Rough estimate
                "parent_id": parent_id,
                "child_ids": child_ids or [],
                "figure_references": self._extract_figure_references(text),
            },
        }

        return chunk

    def _determine_section_and_page(self, text: str, doc_data: dict) -> tuple:
        """
        Determine which document section this chunk comes from and its page number.

        Args:
            text: Chunk text
            doc_data: Document data

        Returns:
            Tuple of (section heading, page_start)
        """
        import re

        # Find section whose content appears in chunk
        for section in doc_data.get("sections", []):
            section_content = section.get("content", "")
            if section_content and section_content[:100] in text:
                return (
                    section.get("heading", "Unknown Section"),
                    section.get("page_start", 1),  # Page number from PDF parser
                )

        # Fallback: try to find page from text markers
        # The PDF parser adds "=== Page N ===" markers
        page_match = re.search(r"=== Page (\d+) ===", text)
        if page_match:
            return (None, int(page_match.group(1)))

        return (None, 1)  # Default to page 1 if unknown

    def _extract_figure_references(self, text: str) -> List[int]:
        """
        Extract explicit figure references from text.

        Args:
            text: Chunk text

        Returns:
            List of figure numbers mentioned
        """
        import re

        # Find "Figure N" patterns
        pattern = r"(?:Figure|Fig\.?)\s+(\d+)"
        matches = re.findall(pattern, text, re.IGNORECASE)

        # Convert to integers
        figure_nums = [int(m) for m in matches]

        return sorted(set(figure_nums))  # Unique, sorted

    def chunk_all_documents(self) -> Dict[str, List[dict]]:
        """
        Chunk all processed documents.

        Returns:
            Dictionary mapping document_id to list of chunks
        """
        json_files = sorted(PROCESSED_DIR.glob("*.json"))
        logger.info(f"Found {len(json_files)} processed documents to chunk")

        all_results = {}

        for json_path in json_files:
            try:
                # Load processed document
                with open(json_path, "r", encoding="utf-8") as f:
                    doc_data = json.load(f)

                # Chunk document
                chunks = self.chunk_document(doc_data)

                # Store results
                doc_id = doc_data["document_id"]
                all_results[doc_id] = chunks

                # Save chunks to file
                output_path = CHUNKS_DIR / f"{doc_id}_chunks.json"
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(chunks, f, indent=2, ensure_ascii=False)

                logger.info(f"Saved {len(chunks)} chunks to {output_path.name}")

            except Exception as e:
                logger.error(f"Failed to chunk {json_path.name}: {e}")
                continue

        return all_results


def chunk_document(doc_path: str) -> List[dict]:
    """Convenience function to chunk a single document."""
    chunker = SemanticChunker()
    with open(doc_path, "r", encoding="utf-8") as f:
        doc_data = json.load(f)
    return chunker.chunk_document(doc_data)


def chunk_all_documents() -> Dict[str, List[dict]]:
    """Convenience function to chunk all documents."""
    chunker = SemanticChunker()
    return chunker.chunk_all_documents()
