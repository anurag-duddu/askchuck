# PRD-03: Chunking & Enrichment Implementation Plan

**Goal:** Transform processed documents into semantically-aware hierarchical chunks with contextual enrichment

**Architecture:** Hierarchical chunking (parents + children), semantic boundaries, contextual prefixes, Owen terminology tagging

**Tech Stack:** LangChain text splitters, Groq LLM (enrichment), custom Owen glossary

---

## Task 1: Create Owen Glossary Module

**Files:**
- Create: `src/utils/owen_glossary.py`

**Implementation:**
Define Owen's Structured Planning terminology for tagging and enrichment

**Steps:**
1. Create glossary dictionary with terms, definitions, examples, related terms
2. Add term extraction function
3. Add term tagging function for chunks

**Verification:**
```python
from src.utils.owen_glossary import OWEN_GLOSSARY, extract_owen_terms
text = "The Function Structure shows how Design Factors relate to Speculations"
terms = extract_owen_terms(text)
print(terms)  # Should find: Function Structure, Design Factors, Speculations
```

**Commit:** `feat: add Owen terminology glossary`

---

## Task 2: Create Semantic Chunker

**Files:**
- Create: `src/chunking/semantic_chunker.py`

**Implementation:**
Chunk documents using semantic separators and hierarchical structure

**Steps:**
1. Create SemanticChunker class
2. Define Owen-specific separators (sections, paragraphs, figure refs, sentences)
3. Implement parent chunking (2048 tokens)
4. Implement child chunking (512 tokens)
5. Track parent-child relationships
6. Create chunk metadata

**Verification:**
```python
from src.chunking.semantic_chunker import SemanticChunker
chunker = SemanticChunker()
doc = load_processed_doc("data/processed/<doc>.json")
chunks = chunker.chunk_document(doc)
print(f"Created {len(chunks)} chunks")
```

**Commit:** `feat: add semantic chunker with hierarchical structure`

---

## Task 3: Create Figure Chunk Generator

**Files:**
- Create: `src/chunking/figure_chunker.py`

**Implementation:**
Create dedicated retrievable chunks for figures

**Steps:**
1. Create FigureChunker class
2. Extract figure metadata from processed JSON
3. Create standalone figure chunks (caption + description + metadata)
4. Track dense relationships (explicit "Figure N" references)
5. Track sparse relationships (same section/context)

**Verification:**
```python
from src.chunking.figure_chunker import FigureChunker
chunker = FigureChunker()
figure_chunks = chunker.create_figure_chunks(doc_data)
print(f"Created {len(figure_chunks)} figure chunks")
```

**Commit:** `feat: add figure chunk generator with relationship tracking`

---

## Task 4: Create Contextual Enricher

**Files:**
- Create: `src/chunking/contextual_enricher.py`

**Implementation:**
Add LLM-generated context prefixes to chunks

**Steps:**
1. Create ContextualEnricher class
2. Implement Groq LLM integration
3. Create prompt template for context generation
4. Batch process chunks with rate limiting
5. Prepend context to chunk text

**Verification:**
```python
from src.chunking.contextual_enricher import ContextualEnricher
enricher = ContextualEnricher()
enriched = enricher.enrich_chunk(chunk, doc_metadata)
print(enriched['enriched_text'][:200])
```

**Commit:** `feat: add contextual enricher with Groq LLM`

---

## Task 5: Create Main Chunking Pipeline

**Files:**
- Create: `src/chunking/pipeline.py`
- Create: `scripts/chunk_documents.py`

**Implementation:**
Orchestrate all chunking components

**Steps:**
1. Create ChunkingPipeline class
2. Integrate semantic chunker, figure chunker, contextual enricher
3. Add Owen terminology tagging
4. Generate final chunk output (JSON)
5. Create CLI script

**Verification:**
```bash
python scripts/chunk_documents.py --limit 2
ls data/chunks/
cat data/chunks/<doc>_chunks.json | head -100
```

**Commit:** `feat: add main chunking pipeline`

---

## Task 6: Process All Documents

**Manual step:** Run pipeline on all processed documents

**Verification:**
```bash
python scripts/chunk_documents.py --all
ls data/chunks/ | wc -l  # Should be ~20
```

**Commit:** `chore: process all documents through chunking`

---

## Task 7: Documentation

**Files:**
- Create: `docs/CHUNKING_COMPLETE.md`

**Commit:** `docs: add chunking completion summary`

---

## Simplified Approach (MVP)

If complexity arises, consider:

1. Skip hierarchical structure initially (just child chunks)
2. Simple RecursiveCharacterTextSplitter from LangChain
3. Skip contextual enrichment temporarily
4. Basic Owen term matching

This gets chunking working, then enhance later.

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| ✅ All docs chunked | JSON files in `data/chunks/` |
| ✅ Parent-child relationships | Metadata includes parent_id/child_ids |
| ✅ Semantic boundaries | Chunks don't split mid-sentence |
| ✅ Figure chunks created | Separate chunks for figures |
| ✅ Contextual enrichment | Chunks have context prefixes |
| ✅ Owen terms tagged | Metadata includes terminology tags |
| ✅ Output schema valid | Consistent JSON structure |

---

## Notes

- LangChain's RecursiveCharacterTextSplitter can be used with custom separators
- Contextual enrichment is optional but recommended
- Parent-child relationships can be post-processed if needed
- Rate limiting for Groq API: ~30 RPM
