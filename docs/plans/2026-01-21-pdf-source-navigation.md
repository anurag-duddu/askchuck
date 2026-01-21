# PDF Source Navigation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable users to click on source citations to open the original PDF at the exact page location.

**Architecture:** Upload original PDFs to Supabase Storage, propagate page numbers through the RAG pipeline (parser → chunker → indexer → API → frontend), and add click-to-navigate functionality to the SourceCitations component using PDF.js URL parameters (`#page=N`).

**Tech Stack:** Supabase Storage (PDF hosting), Python (backend pipeline), Next.js/React (frontend), PDF.js URL parameters (navigation)

---

## Task 1: Create PDF Uploader for Supabase Storage

**Files:**
- Create: `src/ingestion/pdf_uploader.py`
- Modify: `src/utils/config.py:51` (add new bucket config)

**Step 1: Add PDF bucket configuration**

In `src/utils/config.py`, add after line 51:

```python
supabase_pdf_bucket: str = "askchuck-pdfs"
```

**Step 2: Create the PDF uploader module**

Create `src/ingestion/pdf_uploader.py`:

```python
"""
PDF upload to Supabase Storage.
Provides public URLs for source PDFs to enable citation navigation.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from supabase import Client, create_client

from src.utils.config import settings, RAW_DIR

logger = logging.getLogger(__name__)


class SupabasePDFUploader:
    """
    Uploads PDF documents to Supabase Storage for web access.
    """

    def __init__(self):
        """Initialize Supabase Storage client for PDFs."""
        if not settings.supabase_url or not settings.supabase_key:
            logger.warning("Supabase credentials not configured - PDF uploader disabled")
            self.client = None
            self.enabled = False
            return

        try:
            self.client: Client = create_client(
                settings.supabase_url, settings.supabase_key
            )
            self.bucket_name = settings.supabase_pdf_bucket
            self.enabled = True
            logger.info(f"Supabase PDF uploader initialized for bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            self.client = None
            self.enabled = False

    def upload_pdf(self, pdf_path: Path) -> Optional[str]:
        """
        Upload a PDF to Supabase Storage and return its public URL.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Public URL if successful, None otherwise
        """
        if not self.enabled:
            logger.debug("Supabase PDF uploader not enabled, skipping upload")
            return None

        try:
            # Use filename as object path
            object_path = f"documents/{pdf_path.name}"

            with open(pdf_path, "rb") as f:
                file_content = f.read()

            # Upload to Supabase Storage
            self.client.storage.from_(self.bucket_name).upload(
                path=object_path,
                file=file_content,
                file_options={"content-type": "application/pdf", "upsert": "true"},
            )

            # Generate public URL
            public_url = f"{settings.supabase_url}/storage/v1/object/public/{self.bucket_name}/{object_path}"

            logger.info(f"Uploaded PDF: {pdf_path.name} -> {public_url}")
            return public_url

        except Exception as e:
            logger.error(f"Failed to upload PDF {pdf_path.name}: {e}")
            return None

    def upload_all_pdfs(self) -> Dict[str, str]:
        """
        Upload all PDFs from RAW_DIR and return mapping of filename to URL.

        Returns:
            Dict mapping PDF filename to public URL
        """
        if not self.enabled:
            logger.warning("PDF uploader not enabled")
            return {}

        pdf_files = list(RAW_DIR.glob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDFs to upload")

        url_mapping = {}
        for pdf_path in pdf_files:
            url = self.upload_pdf(pdf_path)
            if url:
                url_mapping[pdf_path.name] = url

        logger.info(f"Uploaded {len(url_mapping)}/{len(pdf_files)} PDFs successfully")
        return url_mapping

    def get_pdf_url(self, filename: str) -> str:
        """
        Get the public URL for a PDF by filename.

        Args:
            filename: PDF filename (e.g., "document.pdf")

        Returns:
            Public URL for the PDF
        """
        object_path = f"documents/{filename}"
        return f"{settings.supabase_url}/storage/v1/object/public/{self.bucket_name}/{object_path}"


# Global instance cache
_pdf_uploader: Optional[SupabasePDFUploader] = None


def get_pdf_uploader() -> SupabasePDFUploader:
    """Get or create the global PDF uploader instance."""
    global _pdf_uploader
    if _pdf_uploader is None:
        _pdf_uploader = SupabasePDFUploader()
    return _pdf_uploader


def upload_all_pdfs() -> Dict[str, str]:
    """Convenience function to upload all PDFs."""
    return get_pdf_uploader().upload_all_pdfs()
```

**Step 3: Test PDF upload manually**

```bash
cd /Users/anuragduddu/code-projects/askchuck
python -c "from src.ingestion.pdf_uploader import upload_all_pdfs; print(upload_all_pdfs())"
```

**Step 4: Commit**

```bash
git add src/ingestion/pdf_uploader.py src/utils/config.py
git commit -m "feat: add PDF uploader for Supabase Storage"
```

---

## Task 2: Propagate Page Numbers Through Chunker

**Files:**
- Modify: `src/chunking/semantic_chunker.py:162-186` (add page metadata to chunks)

**Step 1: Update _create_chunk to include page_start**

In `src/chunking/semantic_chunker.py`, modify the `_create_chunk` method to accept and store page information. Replace the method (lines 134-186):

```python
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
            "page_start": page_start,  # NEW: Page number for navigation
            "pdf_filename": pdf_filename,  # NEW: PDF filename for URL construction
            "owen_terms": owen_terms,
            "char_count": len(text),
            "approx_tokens": len(text) // 4,
            "parent_id": parent_id,
            "child_ids": child_ids or [],
            "figure_references": self._extract_figure_references(text),
        },
    }

    return chunk
```

**Step 2: Update _determine_section to also return page number**

Replace `_determine_section` method with `_determine_section_and_page`:

```python
def _determine_section_and_page(self, text: str, doc_data: dict) -> tuple[Optional[str], Optional[int]]:
    """
    Determine which document section this chunk comes from and its page number.

    Args:
        text: Chunk text
        doc_data: Document data

    Returns:
        Tuple of (section heading, page_start)
    """
    # Find section whose content appears in chunk
    for section in doc_data.get("sections", []):
        section_content = section.get("content", "")
        if section_content and section_content[:100] in text:
            return (
                section.get("heading", "Unknown Section"),
                section.get("page_start"),  # Page number from PDF parser
            )

    # Fallback: try to find page from text markers
    # The PDF parser adds "=== Page N ===" markers
    import re
    page_match = re.search(r"=== Page (\d+) ===", text)
    if page_match:
        return (None, int(page_match.group(1)))

    return (None, 1)  # Default to page 1 if unknown
```

**Step 3: Commit**

```bash
git add src/chunking/semantic_chunker.py
git commit -m "feat: propagate page numbers through chunker"
```

---

## Task 3: Update Indexing Pipeline to Store Page Metadata

**Files:**
- Modify: `src/indexing/pipeline.py:159-194` (add page_start and pdf_filename to metadata)

**Step 1: Update _prepare_metadata to include page info**

In `src/indexing/pipeline.py`, update the `_prepare_metadata` method:

```python
def _prepare_metadata(self, chunk: dict) -> Dict:
    """
    Prepare chunk metadata for Pinecone.
    Pinecone has size limits, so we keep only essential fields.

    Args:
        chunk: Chunk dictionary

    Returns:
        Filtered metadata dictionary
    """
    metadata = {
        "chunk_id": chunk["chunk_id"],
        "document_id": chunk["document_id"],
        "level": chunk.get("level", "child"),
        "chunk_position": chunk.get("chunk_position", 0),
        # Document metadata
        "document_title": chunk["metadata"].get("document_title", ""),
        "document_author": chunk["metadata"].get("document_author", ""),
        # Chunk metadata
        "source_section": chunk["metadata"].get("source_section", ""),
        "owen_terms": chunk["metadata"].get("owen_terms", [])[:10],
        # NEW: Page navigation metadata
        "page_start": chunk["metadata"].get("page_start", 1),
        "pdf_filename": chunk["metadata"].get("pdf_filename", ""),
        # Hierarchical metadata
        "parent_id": chunk["metadata"].get("parent_id", ""),
        # Figure metadata (if applicable)
        "chunk_type": chunk["metadata"].get("chunk_type", "text"),
        "figure_number": chunk["metadata"].get("figure_number", 0),
        "figure_url": chunk["metadata"].get("figure_url", ""),
        # Text (for display in results)
        "text": chunk["text"][:1000],
    }

    # Remove empty/null values (but keep page_start even if 0)
    metadata = {
        k: v for k, v in metadata.items()
        if v not in [None, "", []] or k in ["chunk_position", "figure_number", "page_start"]
    }

    return metadata
```

**Step 2: Commit**

```bash
git add src/indexing/pipeline.py
git commit -m "feat: include page metadata in Pinecone index"
```

---

## Task 4: Update RAG Chain to Pass Page Info to Frontend

**Files:**
- Modify: `src/generation/rag_chain.py:260-286` (_build_sources_list method)

**Step 1: Update _build_sources_list to include page_start and pdf_url**

```python
def _build_sources_list(self, chunks: List[dict]) -> List[dict]:
    """
    Build deduplicated list of sources in [Document, Section] format.
    Includes page number and PDF URL for navigation.
    """
    from src.ingestion.pdf_uploader import get_pdf_uploader

    sources = []
    seen = set()
    pdf_uploader = get_pdf_uploader()

    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        doc_title = chunk.get("document_title", "Unknown")
        section = chunk.get("section", "")
        page_start = metadata.get("page_start") or chunk.get("page_start", 1)
        pdf_filename = metadata.get("pdf_filename") or chunk.get("pdf_filename", "")

        key = (doc_title, section)

        if key not in seen:
            # Build PDF URL with page anchor
            pdf_url = ""
            if pdf_filename:
                base_url = pdf_uploader.get_pdf_url(pdf_filename)
                pdf_url = f"{base_url}#page={page_start}"

            sources.append(
                {
                    "display": f"[{doc_title}, {section}]" if section else f"[{doc_title}]",
                    "document": doc_title,
                    "section": section,
                    "chunk_id": chunk.get("chunk_id"),
                    "chunk_level": chunk.get("chunk_level", "unknown"),
                    # NEW: Navigation fields
                    "page_start": page_start,
                    "pdf_url": pdf_url,
                }
            )
            seen.add(key)

    return sources
```

**Step 2: Commit**

```bash
git add src/generation/rag_chain.py
git commit -m "feat: include PDF URL and page number in sources"
```

---

## Task 5: Update Frontend Types

**Files:**
- Modify: `askchuck-frontend/src/types/chat.ts:11-17` (Source interface)

**Step 1: Add page_start and pdf_url to Source interface**

```typescript
export interface Source {
  display: string;
  document: string;
  section: string;
  chunk_id: string;
  chunk_level: string;
  // NEW: Navigation fields
  page_start?: number;
  pdf_url?: string;
}
```

**Step 2: Commit**

```bash
git add askchuck-frontend/src/types/chat.ts
git commit -m "feat: add navigation fields to Source type"
```

---

## Task 6: Update SourceCitations Component for Click-to-Navigate

**Files:**
- Modify: `askchuck-frontend/src/components/chat/SourceCitations.tsx`

**Step 1: Add click handler and external link icon**

Replace the entire component:

```tsx
"use client";

import { useState } from "react";
import { Source } from "@/types/chat";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ChevronDown, ChevronUp, FileText, ExternalLink } from "lucide-react";

interface SourceCitationsProps {
  sources: Source[];
}

export function SourceCitations({ sources }: SourceCitationsProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const handleSourceClick = (source: Source) => {
    if (source.pdf_url) {
      window.open(source.pdf_url, "_blank", "noopener,noreferrer");
    }
  };

  return (
    <div className="space-y-3">
      {/* Expandable header - footnote style */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-4 py-3 rounded-sm border border-border bg-muted/30 hover:bg-muted/50 transition-all duration-300 group"
      >
        <div className="flex items-center gap-3">
          <FileText className="w-4 h-4 text-primary" />
          <span className="text-sm font-serif text-foreground">
            <span className="text-primary font-semibold">{sources.length}</span>{" "}
            {sources.length === 1 ? "Source" : "Sources"} Referenced
          </span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
        ) : (
          <ChevronDown className="w-4 h-4 text-muted-foreground group-hover:text-primary transition-colors" />
        )}
      </button>

      {/* Expanded source list */}
      {isExpanded && (
        <div className="space-y-3 animate-in slide-in-from-top-2 duration-500">
          {sources.map((source, index) => (
            <Card
              key={source.chunk_id}
              onClick={() => handleSourceClick(source)}
              className={`p-4 border border-border bg-card transition-all duration-300 animate-in fade-in slide-in-from-left-2 ${
                source.pdf_url
                  ? "cursor-pointer hover:border-primary hover:bg-primary/5"
                  : ""
              }`}
              style={{ animationDelay: `${index * 100}ms` }}
            >
              {/* Source header */}
              <div className="flex items-start justify-between gap-4 mb-3">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="font-mono text-xs border-primary/50 text-primary">
                    [{index + 1}]
                  </Badge>
                  <span className="text-sm font-serif font-medium text-foreground">
                    {source.display}
                  </span>
                  {source.pdf_url && (
                    <ExternalLink className="w-3 h-3 text-muted-foreground" />
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {source.page_start && (
                    <Badge variant="outline" className="text-xs font-mono">
                      p. {source.page_start}
                    </Badge>
                  )}
                  <Badge variant="secondary" className="text-xs font-mono flex-shrink-0">
                    {source.chunk_level}
                  </Badge>
                </div>
              </div>

              {/* Document and section */}
              <div className="text-xs text-muted-foreground mb-2">
                {source.document} • {source.section}
              </div>

              {/* Click hint when PDF available */}
              {source.pdf_url && (
                <div className="text-xs text-primary/70 flex items-center gap-1">
                  <ExternalLink className="w-3 h-3" />
                  Click to open PDF at page {source.page_start || 1}
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add askchuck-frontend/src/components/chat/SourceCitations.tsx
git commit -m "feat: add click-to-navigate PDF functionality"
```

---

## Task 7: Create Supabase Bucket and Upload PDFs

**Step 1: Create the askchuck-pdfs bucket in Supabase**

Go to Supabase Dashboard > Storage > Create new bucket:
- Name: `askchuck-pdfs`
- Public bucket: Yes (for public URL access)

Or via SQL in Supabase SQL Editor:
```sql
INSERT INTO storage.buckets (id, name, public)
VALUES ('askchuck-pdfs', 'askchuck-pdfs', true);
```

**Step 2: Run PDF upload script**

```bash
cd /Users/anuragduddu/code-projects/askchuck
python -c "from src.ingestion.pdf_uploader import upload_all_pdfs; result = upload_all_pdfs(); print(f'Uploaded {len(result)} PDFs'); print(result)"
```

**Step 3: Verify uploads in Supabase Dashboard**

Check Storage > askchuck-pdfs > documents/ for uploaded files.

---

## Task 8: Re-index Chunks with Page Metadata (Optional - for existing data)

**Note:** This task is only needed if you want existing indexed data to have page numbers. New ingestion runs will automatically include page metadata.

**Step 1: Re-run chunking pipeline**

```bash
cd /Users/anuragduddu/code-projects/askchuck
python -c "from src.chunking.semantic_chunker import chunk_all_documents; chunk_all_documents()"
```

**Step 2: Re-run indexing pipeline**

```bash
python -c "from src.indexing.pipeline import index_all_chunks; index_all_chunks()"
```

---

## Task 9: End-to-End Test

**Step 1: Start the backend**

```bash
cd /Users/anuragduddu/code-projects/askchuck
python -m src.api.server
```

**Step 2: Start the frontend**

```bash
cd /Users/anuragduddu/code-projects/askchuck/askchuck-frontend
npm run dev
```

**Step 3: Test the feature**

1. Open http://localhost:3000
2. Ask a question (e.g., "What is a design factor?")
3. Expand the Sources section
4. Click on a source card
5. Verify: New tab opens with PDF at the correct page

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete PDF source navigation feature

- Upload PDFs to Supabase Storage
- Propagate page numbers through RAG pipeline
- Add click-to-navigate in SourceCitations component
- Sources now show page numbers and open PDFs in new tab"
```

---

## Summary

| Task | Component | Key Changes |
|------|-----------|-------------|
| 1 | PDF Uploader | New `src/ingestion/pdf_uploader.py` |
| 2 | Chunker | Add `page_start`, `pdf_filename` to metadata |
| 3 | Indexer | Include page metadata in Pinecone |
| 4 | RAG Chain | Build PDF URLs with page anchors |
| 5 | Frontend Types | Add `page_start`, `pdf_url` to Source |
| 6 | SourceCitations | Click handler + UI updates |
| 7 | Supabase | Create bucket, upload PDFs |
| 8 | Re-index | Optional: update existing data |
| 9 | Test | End-to-end verification |
