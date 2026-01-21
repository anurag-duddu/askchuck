# PRD Review Tracker

This document tracks the review status and decisions for each PRD in the AskChuck project.

**Review Process:**
1. Discuss each PRD one at a time
2. Document decisions and changes needed
3. Update the PRD with finalized content
4. Mark as finalized and move to next

---

## Review Status Summary

| PRD | Title | Status | Version |
|-----|-------|--------|---------|
| PRD-00 | Overview | ✅ Finalized | v2.0 |
| PRD-01 | Environment Setup | ✅ Finalized | v2.0 |
| PRD-02 | Document Ingestion | ✅ Finalized | v2.0 |
| PRD-03 | Chunking & Enrichment | ✅ Finalized | v2.0 |
| PRD-04 | Indexing | ✅ Finalized | v2.0 |
| PRD-05 | Retrieval | ✅ Finalized | v2.0 |
| PRD-06 | Generation | ✅ Finalized | v2.0 |
| PRD-07 | Frontend | ✅ Finalized | v2.0 |
| PRD-08 | Evaluation | ✅ Finalized | v2.0 |
| PRD-09 | Deployment | ✅ Finalized | v2.0 |

**Legend:** ⏳ Pending | 🔄 In Review | ✅ Finalized | ❌ Removed | 🆕 New

---

## PRD-00: Overview

### User Feedback (v1.0)
- **Vector Database:** Initially considered Chroma Cloud, switched to **Pinecone** (Chroma only $5 credits, not $100)
- **LLM Provider:** Keep **Groq** (free tier)
- **Corpus:** Remove Dublin paper (not a Charles Owen paper) → **20 papers total**
- **Production Focus:** This is a production system, not an academic project
- **Existing System:** Evaluated - rebuild from scratch (basic LangChain tutorial, poor quality)
- **Embeddings:** Use **Voyage AI** for quality (top-ranked for RAG retrieval)
- **Reranking:** Use **Cohere rerank-v3.0** (model diversity from embeddings)
- **File Storage:** Use **Cloudflare R2** for PDFs and figures
- **Hybrid Search:** Pinecone native hybrid search (dense + sparse in one query)

### Decisions Made
| Decision | Choice | Rationale |
|----------|--------|-----------|
| Vector DB | Pinecone (Serverless) | Free tier: 2GB, unlimited queries, native hybrid search |
| Hybrid Search | Pinecone Native | Dense + sparse vectors, no manual BM25/RRF needed |
| Embeddings | Voyage AI (voyage-3) | Best-in-class for RAG, free 200M tokens/mo |
| Reranking | Cohere rerank-v3.0 | Best-in-class, model diversity from embeddings |
| LLM | Groq (Llama 3.3 70B) | Free tier, fast inference |
| File Storage | Cloudflare R2 | Free 10GB, generous request limits |
| Corpus size | 20 papers | Removed non-Owen Dublin paper |
| Existing system | Rebuild from scratch | Poor quality, basic tutorial build |

### SOTA Techniques Included
| Technique | Implementation | PRD |
|-----------|----------------|-----|
| Hybrid search (dense + sparse) | Pinecone native | PRD-05 |
| Contextual enrichment | Groq LLM prepends context | PRD-03 |
| Query expansion | Groq LLM expands queries | PRD-05 |
| Structured figure retrieval | Separate figure matching | PRD-02/05 |

### Open Questions
- [x] Embedding model? → Voyage AI
- [x] File storage? → Cloudflare R2
- [x] Reranking? → Cohere rerank-v3.0
- [x] Vector DB? → Pinecone (switched from Chroma due to $5 vs free tier limits)
- [x] Hybrid search? → Pinecone native

### Changes Required for PRD-00 Document
- [x] Update architecture diagram with new tech stack
- [x] Update technology stack table
- [x] Add Pinecone, Voyage AI, Cohere, Cloudflare R2
- [x] Add native hybrid search architecture
- [x] Add SOTA techniques section
- [x] Reflect production-grade focus throughout

### Status: ✅ Finalized (v2.0)

---

## PRD-01: Environment Setup

### User Feedback (v1.0)
- **Docling:** User unsure, requested alternatives
- **Version Pinning:** Yes, follow best practices for reproducibility
- **Authentication:** Use WorkOS, Auth0, or Clerk instead of custom/Supabase Auth
- **Supabase:** User "not thrilled" - needs alternative
- **PDF Parsing Approach:** Focus on figure-level retrieval, not page-level. Owen's concepts are semantically distinct (text easy), but figures need precision. Extract and describe individual diagrams for multi-modal retrieval quality.
- **Evaluation First:** Test actual PDFs (vector vs raster images) before committing to parsing library

### Decisions Made
| Decision | Choice | Rationale |
|----------|--------|-----------|
| Version pinning | Yes | Reproducibility and best practices |
| Auth provider | Clerk | Best DX, 10K MAU free, requires custom domain |
| Database | Not needed | Cloudflare R2 for file storage, Pinecone for vectors |
| PDF parsing | Evaluate first | Test PyMuPDF on sample papers to assess extraction complexity |
| Figure strategy | Figure-level retrieval | Extract individual figures with descriptions for precise retrieval |
| Low-res figure handling | Multi-level fallbacks | Detection (DPI/OCR checks) → Extraction fallbacks (multiple strategies) → Description fallbacks (vision → OCR+text → caption-only) → Human review for critical failures |

### Open Questions
- [ ] After PDF evaluation: PyMuPDF sufficient or need Unstructured/LlamaParse?
- [ ] How to handle vector vs raster image extraction?
- [ ] Custom domain setup timeline for Clerk (Clerk doesn't work on free Vercel deployments)
- [ ] What to do when extracted image resolution is insufficient for vision model?

### Changes Required
- [x] Add Pinecone account setup (remove Chroma)
- [x] Add Voyage AI account setup (remove HuggingFace)
- [x] Add Cloudflare R2 account setup (remove Supabase)
- [x] Add Clerk account setup (note custom domain requirement)
- [x] Update requirements.txt with version pinning
- [x] Update config.py with new services
- [x] Add PDF evaluation section (test extraction on sample papers)
- [x] Document figure-level extraction requirements
- [x] Add low-resolution figure handling strategy:
  - Quality assessment (DPI, resolution, OCR confidence checks)
  - Multi-strategy extraction cascade (vector → high-DPI pixmap → pdf2image)
  - Description fallback chain (Groq Vision → OCR+text → caption-only)
  - Human review workflow for low-confidence figures
  - Retrieval fallbacks (description → caption → page context)

### Status: ✅ Finalized (v2.0)

---

## PRD-02: Document Ingestion

### User Feedback (v1.0)
- **Groq Rate Limits:** Free tier limits shared (see below). Acceptable for one-time processing
- **Caption Detection:** Good catch - needs preemptive fix before building
- **Document Identifiers:** Need more comprehensive unique identifiers
- **Groq Usage Clarification:** Groq ONLY used for figure descriptions (Groq Vision API), NOT for PDF parsing or extraction
- **Ralph Loop:** User has Ralph Loop plugin installed, can run ingestion in background terminal

### Groq Free Tier Limits (Reference)
- llama-3.3-70b-versatile: 30 RPM, 1K RPD, 12K TPM, 100K TPD
- llama-3.1-8b-instant: 30 RPM, 14.4K RPD, 6K TPM, 500K TPD
- llama-3.2-vision: Used for figure descriptions (~150 figures × 5 sec = 12 min with rate limits)

### Decisions Made
| Decision | Choice | Rationale |
|----------|--------|-----------|
| Rate limit handling | Ralph Loop in background | One-time processing, handles retries automatically |
| Checkpointing | Simple file-exists check | Skip already processed papers, resume on interruption |
| Document identifiers | Comprehensive schema | Include filename, source, publication date, hash for versioning |
| Caption detection | Multi-pattern matching | Handle "Figure 1", "Fig 1", multi-line captions, captions above/below |
| Output schema | Keep current + enhancements | Add content hash, figure quality scores, processing metadata |
| Groq usage | ONLY figure descriptions | PDF parsing/extraction uses Python libraries (PyMuPDF/etc) |

### Open Questions
- [ ] After PDF evaluation: final parsing library choice?

### Changes Required
- [ ] Replace Supabase with Cloudflare R2 throughout
- [ ] Update document identifier schema (add hash, source metadata)
- [ ] Add caption detection patterns (multiple formats, positions)
- [ ] Add simple checkpointing (check if JSON exists)
- [ ] Clarify Groq is ONLY for figure descriptions
- [ ] Add Ralph Loop usage note for background processing
- [ ] Add figure quality assessment integration
- [ ] Update all code examples with new tech stack

### Status: ✅ Finalized (v2.0)

---

## PRD-03: Chunking & Enrichment

### User Feedback (v1.0)
- **Fixed Chunking:** ❌ Rejected - user explicitly does not want fixed 512-token chunks
- **Intelligent Chunking:** Wants semantic chunking and contextual chunking
- **Glossary:** Current list is a start, not complete
- **Chunk Retrieval:** Need to understand scenarios better before deciding on chunk count limits
- **Hybrid Hierarchical Approach:** Sophisticated multi-strategy chunking combining semantic breaks, parent-child relationships, and contextual interrelations

### Decisions Made
| Decision | Choice | Rationale |
|----------|--------|-----------|
| Chunking strategy | Hybrid hierarchical | LlamaIndex for parent-child + custom semantic boundaries + figure-text relationships |
| Implementation library | LlamaIndex HierarchicalNodeParser | Automatic parent-child tracking, proven reliability |
| Semantic boundaries | Custom Owen-specific separators | Sections, paragraphs, figures, sentences - respects document structure |
| Hierarchical levels | 2 levels (parent/child) | Parent: 2048 tokens, Child: 512 tokens (targets, not hard limits) |
| Parent-child tracking | LlamaIndex automatic | Eliminates need for manual relationship graph construction |
| Figure-text relationships | Custom post-processing | Dense (explicit "Figure N") + Sparse (contextual relevance) |
| Contextual interrelations | Preserved via metadata | Parent context, neighboring chunks, related figures, Owen terms |
| Boundary validation | Glossary-aware | Avoid splitting Owen terminology mid-concept |
| Glossary expansion | Manual curation + validation | Existing glossary is comprehensive, validate during chunking |
| Contextual enrichment | Keep | LLM-generated prefixes remain essential |
| Figure chunks | Keep | Standalone figure chunks with descriptions |

### Hybrid Chunking Implementation Details

**Three-part hybrid approach:**

1. **LlamaIndex HierarchicalNodeParser:**
   - Handles all parent-child relationship tracking automatically
   - Uses custom SentenceSplitter with Owen-specific semantic separators
   - Maintains bidirectional links in node relationships
   - Target sizes: Parent (2048 tokens), Child (512 tokens) - flexible based on content

2. **Custom Semantic Separators (Owen-Specific):**
   ```python
   separators = [
       "\n## ",      # Section headings
       "\n### ",     # Subsection headings
       "\nFigure ",  # Figure references
       "\n\n",       # Paragraph breaks
       "\n",         # Line breaks
       ". ",         # Sentence boundaries
   ]
   ```

3. **Post-Processing for Figure-Text Relationships:**
   - **Dense links:** Find explicit "Figure 1" references in chunk text using regex
   - **Sparse links:** Find figures from same section or contextually related
   - **Metadata enrichment:** Add `explicit_figures` and `related_figures` arrays to chunk metadata

4. **Glossary Validation:**
   - Check chunk boundaries don't split Owen terms
   - Current glossary covers core concepts comprehensively
   - Validate during chunking, not runtime expansion

### Updated Chunk Schema

```json
{
  "chunk_id": "owen_power_of_abstraction_2009_chunk_005",
  "document_id": "owen_power_of_abstraction_2009",
  "chunk_type": "text",
  "parent_id": "owen_power_of_abstraction_2009_chunk_002",  // NEW
  "child_ids": ["..._chunk_011", "..._chunk_012"],          // NEW
  "original_text": "...",
  "enriched_text": "...",
  "metadata": {
    "document_title": "The Power of Abstraction",
    "section": "The Abstraction Ladder",
    "section_hierarchy": ["Introduction", "Core Concepts", "The Abstraction Ladder"],  // NEW
    "page_start": 3,
    "page_end": 3,
    "owen_terms": ["Abstraction Ladder", "Function"],
    "explicit_figures": ["owen_power_of_abstraction_2009_fig_1"],    // NEW - dense
    "related_figures": ["owen_power_of_abstraction_2009_fig_2"],     // NEW - sparse
    "neighbor_chunk_ids": ["..._chunk_004", "..._chunk_006"],        // NEW
    "token_count": 487,
    "char_count": 2156,
    "chunk_level": "child"  // NEW - "parent" or "child"
  }
}
```

### Open Questions
- [x] Implementation: LlamaIndex HierarchicalNodeParser with SentenceSplitter
- [x] Hierarchy levels: 2 (parent 2048 tokens, child 512 tokens)
- [x] Figure-text relationships: Post-processing with dense + sparse links
- [x] Glossary expansion: Manual validation, existing coverage is comprehensive

### Changes Required
- [x] Document hybrid hierarchical approach with LlamaIndex
- [x] Specify Owen-specific semantic separators
- [x] Define parent-child relationship schema
- [x] Define figure-text relationship schema (dense + sparse)
- [x] Update chunk schema with hierarchical metadata
- [ ] Rewrite implementation code in PRD-03 document

### Status: ✅ Finalized (v2.0)

---

## PRD-04: Indexing

### User Feedback (v1.0 - Session 6)
- **Vector DB:** Switched from Chroma to Pinecone Serverless
- **Embeddings:** Switched from BGE to Voyage AI voyage-3 (1024-dim)
- **Hybrid Search:** Use Pinecone native hybrid search (no manual BM25 index)
- **Hierarchical Indexing:** Index BOTH parent and child chunks for retrieval flexibility
- **Figure Chunks:** Same index, filter by metadata (`chunk_type="figure"`)
- **Sparse Vectors:** Use pinecone-text BM25Encoder (recommended by Pinecone)

### Decisions Made
| Decision | Choice | Rationale |
|----------|--------|-----------|
| Vector database | Pinecone Serverless | Native hybrid search, 2GB free tier, unlimited queries |
| Embedding model | Voyage AI voyage-3 | Best-in-class RAG performance, 1024-dim, 200M tokens/month free |
| Hybrid search | Pinecone native | Built-in BM25F + automatic RRF fusion, eliminates ~400 LOC |
| Sparse vector generation | pinecone-text BM25Encoder | Official Pinecone library, consistent tokenization |
| Hierarchical indexing | Index both parent AND child | Retrieval flexibility - broad queries match parents, specific queries match children |
| Parent chunks indexed | Yes (~250 chunks) | Broader conceptual context (2048 tokens) |
| Child chunks indexed | Yes (~500 chunks) | Precise specific passages (512 tokens) |
| Figure chunks indexed | Yes (~150 chunks) | Same index, filtered by `chunk_type="figure"` |
| Index structure | Single unified index | Simpler maintenance, metadata filtering for chunk types |
| Metadata storage | Flat structure (Pinecone requirement) | Arrays as comma-separated strings, no nested objects |
| BM25 encoder persistence | Saved to disk (data/bm25_encoder.json) | Required for query-time sparse vector generation |

### Technical Implementation
**Embedding Pipeline:**
- Voyage AI voyage-3: 1024-dimensional dense vectors
- Input types: `document` for indexing, `query` for retrieval
- Batch size: 128 chunks per API call
- Total tokens: ~540K (0.27% of 200M free tier)

**Sparse Vector Pipeline:**
- pinecone-text BM25Encoder fitted on corpus
- Generates {"indices": [...], "values": [...]} format
- Encoder serialized for query-time usage

**Pinecone Index:**
- Name: "askchuck"
- Dimension: 1024
- Metric: cosine
- Spec: Serverless (AWS us-east-1)
- Total vectors: ~900 (parents + children + figures)
- Storage: ~7-10MB (well under 2GB free tier)

**Upsert Format:**
```python
{
    "id": chunk_id,
    "values": [dense_vector],  # 1024-dim from Voyage AI
    "sparse_values": {"indices": [...], "values": [...]},  # From BM25Encoder
    "metadata": {
        "chunk_id": str,
        "document_id": str,
        "chunk_type": "text" | "figure",
        "chunk_level": "parent" | "child" | "independent",
        "parent_id": str,  # If child chunk
        "document_title": str,
        "section": str,
        "owen_terms": str,  # Comma-separated
        "text": str  # Enriched text for display
    }
}
```

### Code Structure
**New files created:**
- `src/indexing/embeddings.py` - Voyage AI embedding generation
- `src/indexing/sparse_encoder.py` - BM25 sparse vector generation with pinecone-text
- `src/indexing/pinecone_store.py` - Pinecone index management and hybrid upsertion
- `scripts/build_index.py` - End-to-end indexing pipeline

**Files removed from v1.0:**
- `src/indexing/bm25_index.py` - No longer needed (Pinecone handles BM25 internally)
- All Chroma-related code

### Open Questions
- [x] Which vector database? **Pinecone Serverless**
- [x] Which embedding model? **Voyage AI voyage-3**
- [x] Manual BM25 index or use Pinecone native? **Pinecone native**
- [x] Index parent chunks only or both parent and child? **Both**
- [x] Separate figure index or same index? **Same index, metadata filtering**
- [x] Sparse vector generation library? **pinecone-text BM25Encoder**

### Changes Required
- [x] Complete rewrite from Chroma to Pinecone
- [x] Switch from BGE to Voyage AI embeddings
- [x] Remove manual BM25 indexing code
- [x] Add hierarchical chunk indexing logic
- [x] Update metadata schema for Pinecone constraints
- [x] Add pinecone-text BM25Encoder integration

### Status: ✅ Finalized (v2.0)

---

## PRD-05: Retrieval

### User Feedback (v1.0 - Session 7)
- **Architecture:** Switched from Chroma+BM25 dual retrieval to Pinecone native hybrid search
- **RRF Fusion:** Eliminated manual implementation - Pinecone handles automatically
- **Alpha Parameter:** Start with 0.5 (equal weight), tune during evaluation
- **Hierarchical Expansion:** Option C - retrieve children, add parents, rerank together (Option D user-triggered expansion supported later)
- **Retrieval Counts:** Keep 50 → 5 pipeline (initial_k=50, final_k=5)
- **Query Expansion:** Optional (off by default), uses Owen glossary
- **Neighbor Chunks:** Optional retrieval for contextual expansion

### Decisions Made
| Decision | Choice | Rationale |
|----------|--------|-----------|
| Retrieval architecture | Pinecone native hybrid | Eliminates separate Chroma/BM25 indices and manual RRF (~100 LOC savings) |
| Dense/sparse weighting | alpha=0.5 (default) | Equal weight to semantic and lexical, tunable via evaluation |
| Parent-child expansion | Option C (default enabled) | Retrieve children, add high-scoring parents before rerank |
| Expansion threshold | 0.7 | Only expand child chunks scoring >= 0.7 relevance |
| User-triggered expansion | Option D (later) | Support for explicit follow-up questions via chaining |
| Initial retrieval count | 50 candidates | High recall from Pinecone hybrid query |
| Final result count | 5 results | High precision after Cohere reranking |
| Query expansion | Optional (off by default) | LLM-based expansion with Owen glossary |
| Neighbor chunk retrieval | Optional | Fetch adjacent chunks via neighbor_chunk_ids metadata |
| Figure URLs | Cloudflare R2 | Updated from Supabase (r2_url field) |

### Technical Implementation
**Retrieval Pipeline:**
1. Optional query expansion (Groq LLM + Owen glossary)
2. Voyage AI embedding (1024-dim) + BM25Encoder sparse vector
3. Pinecone hybrid query with alpha parameter
4. Optional parent-child expansion (high-scoring children → parents)
5. Cohere rerank-v3.0 (top-5 from 50 candidates)
6. Result enrichment (r2_url, chunk_level, parent_id, owen_terms)

**Alpha Parameter:**
- `0.0` = 100% sparse (pure BM25 keyword matching)
- `0.5` = 50/50 balanced hybrid (default)
- `1.0` = 100% dense (pure semantic similarity)

**Hierarchical Expansion:**
```python
# Retrieve children from Pinecone
candidates = pinecone.query(query_vector, sparse_vector, top_k=50)

# Add parents for high-scoring children
for chunk in candidates:
    if chunk.chunk_level == "child" and chunk.score >= 0.7:
        parent_id = chunk.metadata.parent_id
        if parent_id not in candidates:
            fetch_and_add_parent(parent_id)

# Rerank combined pool (children + parents)
results = cohere.rerank(query, candidates, top_k=5)
```

### Code Structure
**New files created:**
- `src/retrieval/query_expansion.py` - Query expansion with Owen glossary
- `src/retrieval/pinecone_retriever.py` - Pinecone hybrid query wrapper with parent expansion
- `src/retrieval/reranker.py` - Cohere rerank-v3.0 integration
- `src/retrieval/retrieval_pipeline.py` - End-to-end retrieval pipeline

**Files removed from v1.0:**
- `src/retrieval/hybrid_retriever.py` - Replaced with pinecone_retriever.py (no manual RRF)
- All Chroma retrieval code
- All manual BM25 search code

### Configuration Parameters
| Parameter | Default | Tunable |
|-----------|---------|---------|
| alpha | 0.5 | Yes (via evaluation) |
| initial_k | 50 | Yes (speed vs recall) |
| final_k | 5 | Yes (context window) |
| expand_to_parents | True | Yes |
| expansion_threshold | 0.7 | Yes |
| expand_query | False | Yes |

### Open Questions
- [x] Dense vs sparse weighting? **alpha=0.5 default, tune via evaluation**
- [x] Hierarchical expansion strategy? **Option C: retrieve children, add parents, rerank**
- [x] Retrieval counts (initial_k, final_k)? **50 → 5 pipeline**
- [x] Query expansion default behavior? **Off by default, user can enable**
- [x] Neighbor chunk retrieval? **Optional, via metadata neighbor_chunk_ids**

### Changes Required
- [x] Complete rewrite from Chroma+BM25 to Pinecone native hybrid
- [x] Remove manual RRF fusion logic (~100 LOC)
- [x] Add hierarchical parent-child expansion
- [x] Add neighbor chunk retrieval
- [x] Update figure URLs from Supabase to Cloudflare R2
- [x] Add alpha parameter for dense/sparse weighting
- [x] Add query expansion with Owen glossary

### Status: ✅ Finalized (v2.0)

---

## PRD-06: Generation

### User Feedback (v1.0 - Session 8)
- **Model Update:** Should use Llama 3.3 70B (128K context), not Llama 3.1 70B (8K)
- **Context Window Usage:** How much of 128K context should we use?
- **Citation Format:** Prefer simple display format but need chunk IDs for debugging
- **Figure URLs:** Need Cloudflare R2 URLs, not Supabase
- **Figure Limit:** How many figures per response?

### Decisions Made
| Decision | Choice | Rationale |
|----------|--------|-----------|
| LLM model | Llama 3.3 70B (128K context) | Latest model with massive context window upgrade |
| Context window usage | Conservative ~8K tokens | Proven performance from v1.0, fast generation, room to scale later |
| Token budget allocation | System ~800, Glossary ~600, Context ~4K, History ~1K, Response ~1.5K | Balanced allocation leaving 120K tokens for future expansion |
| Citation format | Hybrid: [Document, Section] + chunk_ids | Simple user-facing format, chunk IDs in metadata for debugging |
| Figure URLs | Cloudflare R2 (r2_url field) | Aligned with PRD-02 finalized storage |
| Figure limit | 3 figures maximum | Prevent UI clutter, prioritize by relevance score |
| Conversation history | Last 5 turns (~1K tokens) | Balance context continuity vs token budget |
| Hierarchical chunks | Format both parent/child | Leverage PRD-03/04/05 hierarchical structure |
| Response length | 1500 tokens max | Detailed but focused answers |
| Temperature | 0.2 | Factual responses with controlled creativity |
| Streaming | Supported via stream_query | Better UX for real-time feedback |

### Technical Implementation
**RAG Chain Flow:**
1. Query received
2. Retrieval via PRD-05 pipeline (Pinecone hybrid + parent expansion + Cohere rerank)
3. Prompt construction (system + glossary + context + history)
4. Generation via Groq Llama 3.3 70B
5. Response formatting (citations + figures + chunk_ids)

**Prompt Structure:**
```python
SYSTEM_PROMPT:
- AskChuck persona and role
- Owen terminology glossary (~600 tokens)
- Response guidelines (8 key rules)
- Retrieved context (~4K tokens, formatted with parent/child indicators)
- Conversation history (last 5 turns, ~1K tokens)

USER_PROMPT:
- Current question
- Citation format reminder
```

**Response Format:**
```python
{
    "answer": str,  # Generated response with inline [Document, Section] citations
    "sources": [    # Hybrid citation format
        {
            "display": "[Document, Section]",  # User-facing
            "chunk_id": str,                   # For debugging
            "chunk_level": "parent" | "child"
        }
    ],
    "chunk_ids": [str],  # All chunk IDs used (metadata)
    "figures": [         # Max 3, Cloudflare R2 URLs
        {
            "url": str,           # r2_url from metadata
            "caption": str,
            "document": str,
            "figure_number": int,
            "description": str
        }
    ],
    "chunks_used": int
}
```

### Code Structure
**New files created:**
- `src/generation/prompts.py` - System/user prompt templates, context formatting, glossary integration
- `src/generation/rag_chain.py` - Complete RAG chain orchestration with streaming support

**Key classes:**
- `AskChuckRAG` - Main RAG chain class
  - `query()` - Standard question answering
  - `stream_query()` - Streaming response generation
  - `_generate()` - Groq API wrapper
  - `_extract_display_figures()` - Figure extraction with 3-figure limit
  - `_build_sources_list()` - Hybrid citation format

### Configuration Parameters
| Parameter | Default | Tunable |
|-----------|---------|---------|
| model | llama-3.3-70b-versatile | No (fixed) |
| temperature | 0.2 | Yes (0.1-0.7) |
| max_tokens | 1500 | Yes (500-3000) |
| top_k | 5 | Yes (3-10) |
| max_turns_history | 5 | Yes (3-10) |
| max_figures | 3 | Yes (1-5) |

### Context Window Strategy
**Current usage:** ~8K tokens (conservative)
**Available:** 128K tokens (16x increase from Llama 3.1)
**Future expansion scenarios:**
- 20K tokens: Retrieve 15-20 chunks for complex queries
- 50K tokens: Extensive conversation history + broad document coverage
- 100K+: Multi-document synthesis, long-form generation

**Expansion triggers:**
- Evaluation shows benefit from more context
- User feedback requests longer/richer responses
- Complex multi-step reasoning queries

### Open Questions
- [x] Model version: **Llama 3.3 70B (128K context)**
- [x] Context usage: **Conservative 8K (room to grow)**
- [x] Citation format: **Hybrid (simple display + chunk IDs)**
- [x] Figure limit: **3 figures maximum**

### Changes Required
- [x] Update model from Llama 3.1 → 3.3 70B
- [x] Document 128K context window (using 8K conservatively)
- [x] Update figure URLs: Supabase → Cloudflare R2
- [x] Add hybrid citation format (display + chunk_ids)
- [x] Align with PRD-05 hierarchical retrieval
- [x] Align with PRD-04 Pinecone metadata schema
- [x] Add chunk_level indicators in context formatting
- [x] Add streaming support
- [x] Add LangSmith tracing

### Status: ✅ Finalized (v2.0)

---

## PRD-07: Frontend

### User Feedback (v1.0 - Session 9)
- **Frontend Framework:** Questioned Streamlit - want production-grade alternative
- **Authentication:** Prefer Clerk, Auth0, or WorkOS over Google OAuth
- **Chat Persistence:** Must persist to database (Supabase, MongoDB, or Neon)
- **Streaming:** Dynamic decision, not hardcoded
- **Figure URLs:** Need Cloudflare R2, not Supabase
- **Professional UX:** Need polished, branded experience

### Decisions Made
| Decision | Choice | Rationale |
|----------|--------|-----------|
| Frontend framework | Next.js 14 + React | Production-grade, SSR, full customization, TypeScript support, Vercel free tier |
| UI styling | Tailwind CSS | Utility-first, responsive design, rapid development |
| Authentication | Clerk | Modern auth, 10K MAU free tier, beautiful UI components, easy integration |
| Database | Supabase Postgres | 500MB storage free tier, unlimited requests, row-level security, real-time |
| Streaming | Always stream (SSE) | Real-time token display via Server-Sent Events, better UX |
| State management | Zustand | Lightweight client state (lighter than Redux) |
| Markdown rendering | react-markdown | Standard React markdown library |
| Backend API | FastAPI (Python) | Exposes RAG chain via HTTP/SSE endpoints |
| Backend deployment | Railway / Render | Always-on container (no cold starts), free tier 512MB RAM |
| Frontend deployment | Vercel | Free tier: 100GB bandwidth, edge functions, automatic deployments |
| Session persistence | Supabase tables | chat_sessions + chat_messages with RLS |
| Figure display | Cloudflare R2 URLs | r2_url field from PRD-02, max 3 figures per PRD-06 |
| Citation format | Hybrid (PRD-06 aligned) | [Document, Section] display + chunk_ids in metadata |
| Streaming fallback | Standard query() | Graceful degradation if SSE fails |
| Mobile responsive | Mobile-first | Touch-friendly controls, collapsible sidebar, sticky input |

### Technical Implementation

**Why Next.js Over Streamlit:**
1. Professional appearance (Streamlit looks like prototype)
2. Better performance (SSR, code splitting, image optimization)
3. Full customization (React components vs rigid widgets)
4. SEO and sharing (metadata, Open Graph tags)
5. Deployment flexibility (Vercel free tier, edge functions)
6. TypeScript support (type safety)

**Tech Stack:**
- Framework: Next.js 14 (App Router)
- UI: React 18 + Tailwind CSS
- Auth: Clerk (10K MAU free)
- DB: Supabase Postgres (500MB free)
- State: Zustand
- Backend: FastAPI (Python)
- Hosting: Vercel (frontend), Railway/Render (backend)

**Database Schema (Supabase):**
```sql
chat_sessions (id, user_id, title, created_at, updated_at, message_count)
chat_messages (id, session_id, role, content, figures, sources, chunk_ids, created_at)
```

**API Endpoints:**
- POST /api/query - Streaming SSE endpoint
- GET /api/sessions - List user's chat sessions
- GET /api/sessions/[id] - Get session with messages
- DELETE /api/sessions/[id] - Delete session

**Python Backend (FastAPI):**
- POST /stream_query - Streams RAG response via SSE
- POST /query - Standard (non-streaming) endpoint
- GET /health - Health check

**Streaming Implementation:**
- Next.js API route proxies Python backend SSE stream
- Frontend uses EventSource to consume SSE
- StreamingMessage component displays tokens in real-time
- Saves complete message to Supabase after streaming completes

**Project Structure:**
```
askchuck-frontend/
├── app/
│   ├── layout.tsx (Clerk provider)
│   ├── sign-in/[[...sign-in]]/page.tsx
│   ├── sign-up/[[...sign-up]]/page.tsx
│   ├── chat/page.tsx (main interface)
│   └── api/query/route.ts (SSE streaming)
├── components/
│   ├── chat/ (ChatContainer, MessageList, StreamingMessage, FigureDisplay, SourceCitations)
│   ├── sidebar/ (Sidebar, SessionList, UserProfile)
│   └── ui/ (Button, Modal, Spinner)
├── lib/
│   ├── supabase.ts
│   ├── askchuck-api.ts
│   └── stores/chatStore.ts
└── backend/main.py (FastAPI)
```

### Code Structure
**New files created:**
- `app/api/query/route.ts` - Streaming SSE endpoint (proxies Python backend)
- `components/chat/StreamingMessage.tsx` - Real-time token display component
- `lib/supabase.ts` - Supabase client and session management functions
- `app/layout.tsx` - Root layout with Clerk authentication provider
- `backend/main.py` - FastAPI backend exposing RAG chain via SSE

**Key components:**
- StreamingMessage - Consumes SSE, displays tokens in real-time
- FigureDisplay - Cloudflare R2 images with captions (max 3)
- SourceCitations - Expandable drawer with [Document, Section] format
- Sidebar - Session list, new chat button, user profile
- Supabase schema - chat_sessions + chat_messages with RLS

### Configuration Parameters
| Parameter | Default | Notes |
|-----------|---------|-------|
| CLERK_FREE_TIER | 10,000 MAU | Monthly active users |
| SUPABASE_FREE_TIER | 500MB storage | Unlimited API requests |
| VERCEL_FREE_TIER | 100GB bandwidth | Edge functions included |
| STREAMING_ENABLED | Always on | Real-time token display |
| MAX_FIGURES_DISPLAY | 3 | Aligned with PRD-06 |
| SESSION_TITLE_LENGTH | 50 chars | Auto-generated from first message |

### Open Questions
- [x] Frontend framework? **Next.js 14 + React**
- [x] Authentication? **Clerk**
- [x] Database? **Supabase Postgres**
- [x] Streaming behavior? **Always stream via SSE**

### Changes Required
- [x] Complete rewrite from Streamlit to Next.js
- [x] Add Clerk authentication integration
- [x] Add Supabase Postgres schema and RLS policies
- [x] Add FastAPI backend with SSE streaming
- [x] Add StreamingMessage component with EventSource
- [x] Update figure URLs from Supabase to Cloudflare R2
- [x] Align with PRD-06 hybrid citation format and 3-figure limit

### Status: ✅ Finalized (v2.0)

---

## PRD-08: Evaluation

### User Feedback (v1.0 - Session 10)
- **Golden Dataset:** Keep comprehensive 50+ questions requirement (manual creation by user)
- **Integration Testing:** Focus on RAG evaluation only, not frontend/API integration
- **Deployment Reference:** Keep generic "production deployment" instead of specific targets

### Decisions Made
| Decision | Choice | Rationale |
|----------|--------|-----------|
| Golden dataset size | 50+ questions | Comprehensive evaluation coverage across all query types (definition, procedural, example, relationship, visual, out-of-scope) |
| Dataset creation method | Manual by domain expert | Requires deep Owen methodology knowledge to write expected answers |
| Question categories | 6 types with distribution | Definition (30%), Procedural (25%), Example (20%), Relationship (15%), Visual (10%), Out-of-scope (tested separately) |
| RAGAS metrics | Standard 4-metric suite | Faithfulness, Answer Relevancy, Context Precision, Context Recall |
| Retrieval metrics | Hit Rate, MRR, NDCG | Independent evaluation of Pinecone hybrid retrieval quality |
| Owen-specific checks | Terminology accuracy, figure retrieval | Domain-specific quality dimensions beyond standard RAG metrics |
| LangSmith tracing | Already enabled (PRD-06) | @traceable decorator on RAG chain methods, no additional work |
| Frontend testing | Out of scope for PRD-08 | Focus purely on backend RAG quality; frontend tested during manual QA |
| Baseline targets | Faithfulness > 0.80, Hit Rate@5 > 0.85 | Ambitious but achievable targets for production readiness |

### Technical Implementation
**Evaluation Script:** `scripts/run_evaluation.py`
- Loads golden dataset from `tests/golden_dataset.json`
- Runs RAGAS metrics using ragas library
- Computes retrieval metrics (Hit Rate@1, Hit Rate@5, MRR)
- Checks terminology accuracy against expected_terms
- Validates figure retrieval for visual queries
- Saves results to `tests/evaluation_results.json`

**Golden Dataset Schema:**
```json
{
  "question": "What is a Design Factor?",
  "category": "definition",
  "difficulty": "easy",
  "expected_answer": "A Design Factor is...",
  "expected_sources": ["Context for Creativity"],
  "expected_terms": ["Design Factor", "Observation"],
  "requires_figure": false
}
```

**Metrics Dashboard:**
- RAGAS scores visualized in LangSmith
- Retrieval performance tracked over time
- Terminology accuracy by query category
- Figure retrieval success rate

### Open Questions
- [x] Dataset size? **50+ questions maintained**
- [x] Integration testing? **No, focus on RAG only**
- [x] Deployment reference? **Generic "production"**

### Changes Required
- [x] Update version to v2.0
- [x] Add "Key Changes" section
- [x] Update "Next Steps" to say "production deployment" (not "Streamlit Cloud")
- [x] Note that LangSmith is already implemented

### Status: ✅ Finalized (v2.0)

---

## PRD-09: Deployment

### User Feedback (v1.0 - Session 11)
- **Backend Platform:** Railway preferred over Render (better DX, always-on)
- **Custom Domain:** No, use default URLs (askchuck.vercel.app + Railway default)
- **Staging Environment:** No, production only (simpler workflow)

### Decisions Made
| Decision | Choice | Rationale |
|----------|--------|-----------|
| Frontend deployment | Vercel (free tier) | Next.js optimization, 100GB bandwidth, edge functions, global CDN, auto-deploy from GitHub |
| Backend deployment | Railway (free tier) | $5/month credit, 512MB RAM, always-on (no cold starts), auto-deploy from GitHub, better DX than Render |
| Domain strategy | Default URLs | askchuck.vercel.app + Railway default URL. Simpler setup, no DNS configuration needed |
| Staging environment | Production only | Test locally before pushing. Simpler workflow for solo developer academic project |
| Frontend env vars | Vercel dashboard | NEXT_PUBLIC_* for browser-exposed, private for server-only (CLERK_SECRET_KEY, BACKEND_API_URL) |
| Backend env vars | Railway dashboard | All API keys server-side (Groq, Voyage AI, Pinecone, Cohere, Cloudflare R2, LangSmith) |
| Database setup | Supabase SQL | Create tables (chat_sessions, chat_messages) with row-level security policies via SQL editor |
| Clerk redirect URLs | askchuck.vercel.app | Update Clerk dashboard with Vercel URL after deployment |
| CORS configuration | Backend code | FastAPI middleware allows localhost:3000 (dev) + askchuck.vercel.app (prod) |
| R2 CORS | Cloudflare dashboard | Allow GET/HEAD from askchuck.vercel.app for figure display |
| Auto-deploy | Git push to main | Both Vercel and Railway auto-deploy on push, no manual intervention |
| Secrets management | Dashboard UI | Vercel + Railway environment variable UIs, no .env files in repository |
| Health monitoring | /health endpoint | Backend exposes /health for uptime checks and deployment verification |

### Technical Implementation

**Deployment Order:**
1. Backend → Railway (get URL for frontend config)
2. Frontend → Vercel (get URL for Clerk redirect)
3. Clerk → Update redirect URLs
4. Supabase → Run SQL to create tables + RLS
5. Cloudflare R2 → Add CORS policy
6. Railway → Update CORS for Vercel domain

**Railway Configuration:**
- Root Directory: `/ask_chuck_api`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- 13 environment variables (Groq, Voyage AI, Pinecone, Cohere, Cloudflare R2, LangSmith, app settings)

**Vercel Configuration:**
- Framework: Next.js
- Root Directory: `askchuck-frontend`
- Build Command: `npm run build`
- 5 environment variables (Clerk keys, Supabase URL/key, Backend API URL)

**Supabase Schema:**
```sql
chat_sessions: id, user_id, title, created_at, updated_at, message_count
chat_messages: id, session_id, role, content, figures, sources, chunk_ids, created_at
```

**Free Tier Limits:**
- Groq: 14,400 req/day (monitor daily)
- Voyage AI: 200M tokens/month (using ~540K for indexing)
- Pinecone: 2GB storage, unlimited queries (~10MB usage)
- Cohere: 1,000 calls/month (monitor weekly - scarcest resource)
- Cloudflare R2: 10GB storage, 1M req/month (~15MB usage)
- Supabase: 500MB storage, unlimited requests (<10MB usage)
- Clerk: 10K MAU
- Vercel: 100GB bandwidth/month
- Railway: $5/month credit (~$5/month for 512MB always-on)
- LangSmith: 5K traces/month

### Open Questions
- [x] Backend platform? **Railway**
- [x] Custom domain? **No, use default URLs**
- [x] Staging environment? **No, production only**

### Changes Required
- [x] Complete rewrite from Streamlit Cloud to Vercel + Railway
- [x] Document split frontend/backend deployment
- [x] Add Supabase database schema and RLS policies
- [x] Add Clerk configuration steps
- [x] Add Cloudflare R2 CORS setup
- [x] Add comprehensive environment variables list
- [x] Add deployment step-by-step guide
- [x] Add post-deployment verification checklist
- [x] Add monitoring and maintenance section
- [x] Update free tier limits table

### Status: ✅ Finalized (v2.0)

---

## Cross-Cutting Decisions Needed

These decisions affect multiple PRDs and need to be resolved:

### 1. Database Choice (affects PRD-01, PRD-04, PRD-07)
**Status:** ✅ Resolved
**Decision:** No traditional database needed
- Cloudflare R2 for file storage (PDFs, figures)
- Pinecone for vector storage
- Chat persistence database TBD in PRD-07 (may need lightweight DB for sessions)

### 2. Authentication (affects PRD-01, PRD-07, PRD-09)
**Status:** ✅ Resolved
**Decision:** Clerk
- Best DX, 10K MAU free
- **Requires custom domain** (doesn't work on free Vercel deployments)
- User will acquire domain later

### 3. Frontend Framework (affects PRD-07, PRD-09)
**Status:** ⏳ Pending
**Current:** Streamlit
**Constraint:** Production-grade, not academic-feeling
**Options to evaluate:**
- [ ] Next.js
- [ ] FastAPI + React
- [ ] Other

### 4. Hosting Platform (affects PRD-04, PRD-09)
**Status:** ⏳ Pending (blocked by custom domain)
**Current:** Streamlit Cloud
**Constraint:** Own domain/subdomain, production-grade
**Options to evaluate:**
- [ ] Vercel (preferred, but needs custom domain for Clerk)
- [ ] Railway
- [ ] Fly.io
- [ ] Render
- [ ] Other

### 5. PDF Parsing (affects PRD-01, PRD-02)
**Status:** ⏳ Pending (evaluation phase)
**Approach:** Test sample PDFs first with PyMuPDF, then decide
**Constraint:** Figure-level extraction (not page-level), handles vector + raster
**Focus:** Multi-modal quality through precise figure extraction + descriptions
**Options to evaluate after testing:**
- [ ] PyMuPDF + manual logic (most control)
- [ ] Unstructured (if complex layout needed)
- [ ] LlamaParse (if API approach preferred)

---

## Session Notes

### Session 1 - Initial Review
**Date:** 2026-01-18
**Summary:** Received comprehensive feedback on all PRDs. Key theme: production-grade system, not academic project. Major changes needed to tech stack.

### Session 2 - Pinecone Decision
**Date:** 2026-01-19
**Summary:** Switched from Chroma Cloud to Pinecone. Chroma only offers $5 credits (not $100), making Pinecone's free tier (2GB, unlimited queries) more suitable. Pinecone's native hybrid search also simplifies architecture by eliminating manual BM25/RRF implementation.

### Session 3 - PRD-01 Decisions
**Date:** 2026-01-20
**Summary:** Finalized PRD-01 approach:
- **Auth:** Clerk (requires custom domain, which user will acquire later)
- **Database:** Not needed - Cloudflare R2 for files, Pinecone for vectors
- **PDF Parsing:** Evaluate-first approach - test PyMuPDF on sample Owen papers to assess figure extraction complexity (vector vs raster)
- **Core Insight:** Focus on figure-level retrieval (not page-level) as competitive advantage. Owen's text concepts are semantically distinct, but figures require precise extraction + descriptions for multi-modal quality.
- **Failure Mode Analysis:** Low-resolution extraction breaks the retrieval chain (bad image → poor description → bad embedding → can't find figure). Solution: Multi-level fallback strategy with quality assessment, extraction cascades, description alternatives, and human review workflow for critical failures.

### Session 4 - PRD-02 Decisions
**Date:** 2026-01-20
**Summary:** Finalized PRD-02 (Document Ingestion):
- **Groq Usage:** ONLY for figure descriptions via Vision API, NOT for PDF parsing/extraction
- **Rate Limits:** Use Ralph Loop in background terminal to handle ~150 figure descriptions
- **Checkpointing:** Simple file-exists check to skip already-processed papers
- **Document IDs:** Comprehensive schema with filename, source, date, content hash
- **Caption Detection:** Multi-pattern matching for various formats and positions
- **PDF Evaluation:** Completed in separate tab, library choice finalized
- **Storage:** Cloudflare R2 replaces Supabase throughout

### Session 5 - PRD-03 Finalization
**Date:** 2026-01-20
**Summary:** Finalized PRD-03 (Chunking & Enrichment) with hybrid hierarchical approach:
- **Implementation:** LlamaIndex HierarchicalNodeParser with SentenceSplitter
- **Semantic Boundaries:** Custom Owen-specific separators (sections, paragraphs, figures, sentences)
- **Hierarchy Levels:** 2 levels - Parent (2048 tokens), Child (512 tokens) - targets, not hard limits
- **Parent-Child Tracking:** LlamaIndex automatic relationship management
- **Figure-Text Relationships:** Post-processing adds dense (explicit "Figure N") and sparse (contextual) links
- **Glossary:** Existing coverage is comprehensive, validation during chunking
- **Flexible Sizing:** Semantic coherence prioritized over fixed token counts
- **Enhanced Schema:** Added parent_id, child_ids, section_hierarchy, explicit_figures, related_figures, neighbor_chunk_ids

**Key Insight:** This is truly "hybrid" - combines LlamaIndex's automatic parent-child tracking with custom semantic boundaries and figure-text relationships. Not just one chunking strategy, but multiple working together.

### Session 6 - PRD-04 Finalization
**Date:** 2026-01-20
**Summary:** Finalized PRD-04 (Indexing) with Pinecone native hybrid search:
- **Vector Database:** Switched from Chroma to Pinecone Serverless
- **Embeddings:** Switched from BGE (384-dim) to Voyage AI voyage-3 (1024-dim)
- **Hybrid Search:** Pinecone native (eliminates manual BM25 index and RRF fusion - ~400 LOC savings)
- **Sparse Vectors:** pinecone-text BM25Encoder (official Pinecone library)
- **Hierarchical Indexing:** Index BOTH parent (~250) and child (~500) chunks for retrieval flexibility
- **Figure Chunks:** Same unified index (~150), filtered by `chunk_type="figure"` metadata
- **Index Structure:** Single "askchuck" index with ~900 total vectors (~7-10MB storage)
- **Free Tier:** Pinecone 2GB storage unlimited queries, Voyage AI 200M tokens/month (only using 540K)

**Key Insight:** Pinecone's native hybrid search dramatically simplifies the architecture. One index, one query API, automatic dense+sparse fusion. The combination of hierarchical indexing (parent/child) and hybrid search (semantic/lexical) provides maximum retrieval flexibility.

**Technical Highlights:**
- Upsert format includes both `values` (dense 1024-dim) and `sparse_values` (BM25 indices/values)
- Metadata flattened per Pinecone requirements (no nested objects, arrays as comma-strings)
- BM25 encoder fitted on corpus and persisted to `data/bm25_encoder.json` for query-time usage
- Parent-child relationships preserved in metadata (`parent_id`, `child_ids`)

### Session 7 - PRD-05 Finalization
**Date:** 2026-01-20
**Summary:** Finalized PRD-05 (Retrieval) with Pinecone native hybrid query and hierarchical expansion:
- **Architecture Simplification:** Eliminated Chroma+BM25 dual retrieval (~100 LOC savings from removing manual RRF)
- **Native Hybrid Search:** Single Pinecone query with both dense and sparse vectors, automatic fusion
- **Alpha Parameter:** Default 0.5 (equal weight), tunable via evaluation (0.0=pure BM25, 1.0=pure semantic)
- **Hierarchical Expansion:** Option C - retrieve children, add high-scoring parents (>= 0.7), rerank together
- **Retrieval Pipeline:** 50 candidates from Pinecone → optional parent expansion → 5 results after Cohere rerank
- **Query Expansion:** Optional (off by default) - Groq LLM with Owen glossary
- **Neighbor Chunks:** Optional retrieval via `neighbor_chunk_ids` metadata for contextual reading
- **Figure URLs:** Updated from Supabase to Cloudflare R2 (`r2_url` field)

**Key Insight:** The retrieval pipeline is now dramatically simpler while maintaining SOTA capabilities. Pinecone's native hybrid search eliminates the complexity of managing separate indices and fusion logic. The hierarchical expansion strategy (retrieve children, optionally add parents, rerank everything) provides flexibility for both specific and broad queries. Option D (user-triggered expansion) can be added later for follow-up question chaining.

**Technical Highlights:**
- Query processing: Voyage AI embed + BM25Encoder sparse → single Pinecone hybrid query
- Parent expansion logic: Only high-scoring children (>= 0.7) trigger parent fetch
- Prevents duplicate parents already in results
- Cohere rerank-v3.0 sees combined pool of children + parents for best selection
- Configuration parameters (alpha, initial_k, final_k, expansion_threshold) all tunable

### Session 8 - PRD-06 Finalization
**Date:** 2026-01-20
**Summary:** Finalized PRD-06 (Generation) with Llama 3.3 70B and hybrid citation format:
- **Model Upgrade:** Llama 3.1 70B (8K) → **Llama 3.3 70B (128K context window)**
- **Context Strategy:** Conservative ~8K token usage (proven performance, room to scale to 128K later)
- **Token Budget:** System ~800, Glossary ~600, Context ~4K, History ~1K, Response ~1.5K = 8K total
- **Citation Format:** Hybrid - [Document, Section] for user display, chunk_ids in metadata for debugging
- **Figure URLs:** Updated from Supabase to Cloudflare R2 (r2_url field)
- **Figure Limit:** Maximum 3 figures per response (prevent UI clutter)
- **Conversation History:** Last 5 turns (~1K tokens)
- **Hierarchical Chunks:** Format both parent/child chunks with level indicators
- **Streaming Support:** stream_query() method for real-time token generation
- **LangSmith Tracing:** @traceable decorator on query methods

**Key Insight:** The 128K context window (16x increase from Llama 3.1) gives us massive headroom for future expansion, but conservative 8K usage maintains proven v1.0 performance (fast generation <2s) while leaving 120K tokens available for future features like long-form document synthesis, extensive conversation history, or multi-document comparison. The hybrid citation format (simple [Document, Section] for users, chunk_ids for debugging) provides the best of both worlds.

**Technical Highlights:**
- RAG chain flow: Query → Retrieval (PRD-05) → Prompt construction → Llama 3.3 generation → Response formatting
- System prompt includes Owen glossary, response guidelines, context with parent/child indicators
- Response format: answer (with inline citations) + sources (hybrid format) + chunk_ids + figures (R2 URLs)
- Figure extraction limited to 3, prioritized by retrieval relevance score
- Streaming yields: tokens, figures, sources, chunk_ids, done
- Configuration parameters tunable: temperature (0.2), max_tokens (1500), top_k (5)

**Context Window Expansion Strategy:**
- Current: ~8K conservative (fast, proven)
- Mid-tier: ~20K tokens (15-20 chunks for complex queries)
- High-tier: ~50K tokens (extensive history + broad coverage)
- Triggers: Evaluation benefits, user feedback, complex reasoning queries

### Session 9 - PRD-07 Finalization
**Date:** 2026-01-20
**Summary:** Finalized PRD-07 (Frontend) with complete architecture shift from Streamlit to Next.js:
- **Framework Shift:** Streamlit → **Next.js 14 + React** (production-grade, TypeScript, full customization)
- **Authentication:** Google OAuth → **Clerk** (10K MAU free tier, modern UI components)
- **Database:** No persistence → **Supabase Postgres** (500MB free, row-level security)
- **Streaming:** Added **Server-Sent Events (SSE)** for real-time token display (always enabled)
- **UI Components:** **shadcn/ui** for professional, accessible React components with proper branding
- **Styling:** Tailwind CSS for utility-first responsive design
- **State Management:** Zustand (lighter than Redux)
- **Backend API:** FastAPI (Python) exposing RAG chain via HTTP/SSE endpoints
- **Deployment:** Vercel (frontend free tier), Railway/Render (backend free tier)

**Key Insight:** This is a major architectural upgrade from v1.0's Streamlit prototype. Next.js provides production-grade performance (SSR, code splitting), professional UX (custom React components with shadcn/ui), better SEO (metadata, Open Graph), and deployment flexibility (Vercel edge functions). The combination of Clerk authentication, Supabase persistence, and SSE streaming creates a modern, polished experience suitable for public academic use. The use of shadcn/ui ensures accessible, customizable components that can be properly branded for AskChuck's identity.

**Technical Highlights:**
- Next.js App Router with TypeScript throughout
- Clerk handles auth, Supabase stores chat sessions with RLS policies
- SSE streaming: Next.js API route proxies Python FastAPI backend stream
- StreamingMessage component consumes EventSource and displays tokens in real-time
- Database schema: chat_sessions + chat_messages with figures/sources/chunk_ids
- FastAPI endpoints: /stream_query (SSE), /query (standard), /health
- shadcn/ui components: Button, Modal, Card, etc. with AskChuck branding
- Cloudflare R2 figure URLs with max 3 figures per PRD-06
- Hybrid citation format from PRD-06: [Document, Section] display + chunk_ids metadata

**Why Next.js Over Streamlit:**
1. Professional appearance (Streamlit looks like prototype)
2. Better performance (SSR, automatic code splitting, image optimization)
3. Full customization (React + shadcn/ui vs rigid Streamlit widgets)
4. SEO and sharing (metadata, Open Graph tags for link previews)
5. Deployment flexibility (Vercel free tier, edge functions, global CDN)
6. TypeScript support (type safety, better DX)

**Project Structure:**
- app/: Next.js App Router (layout, pages, API routes)
- components/: React components (chat, sidebar, ui with shadcn/ui)
- lib/: Supabase client, API client, Zustand stores
- backend/: FastAPI main.py with SSE streaming endpoints
- Supabase schema: Two tables with RLS policies for user isolation

### Session 10 - PRD-08 Finalization
**Date:** 2026-01-20
**Summary:** Finalized PRD-08 (Evaluation) with minimal changes - evaluation framework is backend-focused and independent of frontend architecture:
- **Golden Dataset Size:** Maintained 50+ questions requirement for comprehensive coverage
- **Question Categories:** 6 types with distribution - Definition (30%), Procedural (25%), Example (20%), Relationship (15%), Visual (10%), Out-of-scope
- **RAGAS Metrics:** Standard 4-metric suite (Faithfulness, Answer Relevancy, Context Precision, Context Recall)
- **Retrieval Metrics:** Hit Rate@1, Hit Rate@5, MRR, Figure Retrieval Rate
- **Owen-Specific Checks:** Terminology accuracy, figure retrieval for visual queries
- **LangSmith Integration:** Already implemented in PRD-06 (@traceable decorator), no additional work
- **Integration Testing:** Explicitly out of scope - PRD-08 focuses purely on RAG evaluation, not frontend/API testing
- **Deployment Reference:** Updated from "Streamlit Cloud" to generic "production deployment"

**Key Insight:** PRD-08 required minimal updates because evaluation is backend-focused and independent of the Streamlit → Next.js frontend change. The golden dataset must be manually created by someone with deep Owen methodology expertise - this cannot be automated. The 50+ question requirement ensures comprehensive coverage across all query types, though it's a significant manual effort. The evaluation framework (scripts/run_evaluation.py) tests the RAG chain directly via Python imports, not through the frontend, so it works regardless of frontend technology.

**Technical Highlights:**
- Golden dataset schema includes: question, category, difficulty, expected_answer, expected_sources, expected_terms, requires_figure
- Evaluation script runs: RAGAS metrics, retrieval metrics (Hit Rate, MRR), terminology checks, figure retrieval validation
- LangSmith tracing provides observability for debugging retrieval/generation issues
- Results saved to tests/evaluation_results.json for tracking over time
- Baseline targets: Faithfulness > 0.80, Answer Relevancy > 0.75, Hit Rate@5 > 0.85, MRR > 0.60

**Why Minimal Changes:**
- Evaluation tests backend RAG chain, not frontend
- RAGAS metrics are standard and applicable regardless of UI
- LangSmith already set up in PRD-06
- Golden dataset creation is manual work, not code
- Integration testing deferred to manual QA (not automated)

**Next Step:** PRD-09 (Deployment) is the final PRD requiring review. It will need significant updates to reflect Next.js + Vercel deployment (replacing Streamlit Cloud) and FastAPI backend deployment (Railway/Render).

### Session 11 - PRD-09 Finalization
**Date:** 2026-01-20
**Summary:** Finalized PRD-09 (Deployment) with complete rewrite from Streamlit Cloud to Next.js + Vercel + FastAPI + Railway architecture:
- **Frontend Deployment:** Next.js 14 → Vercel (free tier: 100GB bandwidth, auto-deploy from GitHub)
- **Backend Deployment:** FastAPI → Railway (free tier: $5/month credit, 512MB RAM, always-on with no cold starts)
- **Platform Choice:** Railway preferred over Render for better developer experience and always-on service
- **Domain Strategy:** Use default URLs (askchuck.vercel.app + Railway default) to avoid custom domain complexity
- **Staging Environment:** Production only - test locally before pushing for simpler workflow
- **Deployment Order:** Backend first (get URL) → Frontend (get URL) → Configure Clerk/Supabase/R2 → Update CORS
- **Secrets Management:** Vercel dashboard (5 env vars) + Railway dashboard (13 env vars), no .env files in repo
- **Database Setup:** Supabase Postgres with SQL schema (chat_sessions + chat_messages) and RLS policies
- **CORS Configuration:** FastAPI middleware for Vercel domain, R2 bucket policy for figure access
- **Auto-Deploy:** Both platforms auto-deploy on Git push to main branch

**Key Insight:** This deployment represents a significant architectural upgrade from v1.0's Streamlit Cloud monolith. The split frontend/backend approach provides better scalability, independent deployment cycles, and clear separation of concerns. Railway's always-on $5/month free tier eliminates cold start latency that would occur with Render's free tier (which spins down after inactivity). The comprehensive deployment guide covers all service configurations, environment variables, and verification steps needed for production readiness.

**Technical Highlights:**
- **Railway Configuration:** Root directory `ask_chuck_api/`, build with pip, start with uvicorn, 13 env vars
- **Vercel Configuration:** Root directory `askchuck-frontend/`, Next.js framework preset, 5 env vars (public + private)
- **Supabase Schema:** Two tables with RLS policies ensuring user data isolation via Clerk user_id
- **Clerk Setup:** Update redirect URLs to askchuck.vercel.app after deployment
- **Cloudflare R2 CORS:** Allow GET/HEAD from Vercel domain for figure display
- **Health Monitoring:** /health endpoint on Railway for uptime checks

**Free Tier Limits (Critical):**
- Cohere: 1,000 calls/month (scarcest resource - monitor weekly)
- Groq: 14,400 req/day (monitor daily)
- Railway: $5/month credit (~$5/month for always-on service)
- All other services well within limits

**Deployment Order:**
1. Deploy backend to Railway → get URL
2. Deploy frontend to Vercel with backend URL → get URL
3. Update Clerk redirect URLs with Vercel URL
4. Run Supabase SQL to create tables and RLS policies
5. Configure Cloudflare R2 CORS for Vercel domain
6. Update Railway backend CORS to allow Vercel domain
7. Verify end-to-end functionality with test queries

**Post-Deployment Verification (20+ checks):**
- Frontend loads, authentication works, responsive design
- Backend health endpoint, RAG chain initializes, CORS configured
- Query streaming, figure display, source citations, session persistence
- Performance targets: <3s first token, <10s complete response
- LangSmith traces, token counts, error tracking
- Security: no secrets in repo, HTTPS, CORS, RLS enforcement
- Free tier compliance across all 10 services

**Why Railway Over Render:**
1. Always-on service (no cold starts vs Render free tier spins down)
2. Better developer experience (simpler dashboard, faster deploys)
3. $5/month credit sufficient for 512MB RAM always-on container
4. Auto-deploy from GitHub without complex configuration

**Next Steps:**
After PRD-09 deployment is complete, the comprehensive PRD review is finished. All 10 PRDs (PRD-00 through PRD-09) are now finalized to v2.0 and aligned with the production-grade tech stack:
- Pinecone Serverless (hybrid search)
- Voyage AI voyage-3 (embeddings)
- Cohere rerank-v3.0 (reranking)
- Groq Llama 3.3 70B (generation)
- Cloudflare R2 (figure storage)
- Next.js 14 + Vercel (frontend)
- FastAPI + Railway (backend)
- Supabase Postgres (chat persistence)
- Clerk (authentication)
- LangSmith (observability)

The project is now ready for implementation, following the finalized specifications in each PRD.

---

*Last Updated: 2026-01-20*
*All 10 PRDs Finalized (v2.0) - Ready for Implementation*
