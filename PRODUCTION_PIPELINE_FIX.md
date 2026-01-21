# Production Pipeline Fix: Updated Vision Model

## Problem Summary

The Groq vision model `llama-3.2-90b-vision-preview` was deprecated on April 7, 2025. All existing figure descriptions in the pipeline are using **fallback descriptions** (caption-only text) instead of proper AI-generated descriptions.

**Impact:**
- ❌ Figure chunks have minimal semantic content
- ❌ Figure embeddings are poor quality (just captions)
- ❌ Figure retrieval will miss relevant diagrams
- ❌ Generation quality degraded for visual concept queries

## What Was Fixed

✅ Updated vision model in [src/utils/config.py](src/utils/config.py#L30):
```python
groq_vision_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
```

✅ Verified new model works (tested with sample figure)

## What Needs to Be Re-Run

The entire pipeline from description generation onwards must be re-executed:

### Phase 1: Regenerate Descriptions ⚠️ REQUIRED
**Script:** `regenerate_descriptions.py`
**Input:** Existing processed JSON files in `data/processed/`
**Output:** Updated JSON files with proper AI descriptions
**Duration:** ~5-10 minutes (56 figures × 1 sec rate limit)

```bash
# Preview what will be done
python regenerate_descriptions.py --dry-run

# Actually regenerate
python regenerate_descriptions.py
```

### Phase 2: Re-Chunk Documents ⚠️ REQUIRED
**Script:** `scripts/chunk_documents.py` or chunking pipeline
**Input:** Updated processed JSON files
**Output:** New chunk files in `data/chunks/` with proper figure descriptions
**Duration:** ~1-2 minutes

```bash
python scripts/chunk_documents.py
# OR
python -m src.chunking.pipeline
```

### Phase 3: Re-Index to Pinecone ⚠️ REQUIRED
**Script:** Indexing pipeline
**Input:** New chunks with updated figure descriptions
**Output:** Updated Pinecone index with proper figure embeddings
**Duration:** ~5-10 minutes (embedding + upload)

```bash
python scripts/index_to_pinecone.py
# OR
python -m src.indexing.pipeline
```

### Phase 4: Verification ✓ RECOMMENDED
**Test:** Query for visual concepts and verify figure retrieval
**Examples:**
- "Show me the Abstraction Ladder diagram"
- "What does the Information Structure look like?"
- "Explain the concept generation matrix"

```bash
python -m src.retrieval.test_retrieval --query "Abstraction Ladder diagram"
```

---

## Full Pipeline Architecture

```
┌─────────────────────────────────────────────────────┐
│                  COMPLETE PIPELINE                   │
└─────────────────────────────────────────────────────┘

PHASE 1: INGESTION (PRD-02)
├─ PDF Parsing (text + metadata)          ✓ Done
├─ Figure Extraction (300 DPI rendering)  ✓ Done
├─ Figure Upload (Supabase Storage)       ✓ Done
└─ Description Generation                 ❌ NEEDS RE-RUN
   └─ Output: data/processed/*.json

PHASE 2: CHUNKING (PRD-03)
├─ Hierarchical Text Chunking             ⚠️ NEEDS RE-RUN
│  └─ Parent chunks (2048 tokens)
│  └─ Child chunks (512 tokens)
├─ Figure Chunk Creation                  ⚠️ NEEDS RE-RUN
│  └─ Combines caption + description
│  └─ Extracts Owen terms
│  └─ Preserves Supabase URLs
└─ Contextual Enrichment                  ⚠️ NEEDS RE-RUN
   └─ Output: data/chunks/*.json

PHASE 3: INDEXING (PRD-04)
├─ Dense Embeddings (Voyage AI)           ⚠️ NEEDS RE-RUN
│  └─ 1024-dim vectors
├─ Sparse Vectors (BM25)                  ⚠️ NEEDS RE-RUN
│  └─ Fitted on full corpus
└─ Pinecone Upload                        ⚠️ NEEDS RE-RUN
   └─ Hybrid search enabled

PHASE 4: RETRIEVAL (PRD-05)
└─ Query with figure support              ✓ Already works
   └─ Just needs updated index
```

---

## Expected Results After Re-Run

### Before (Fallback Descriptions)
```json
{
  "chunk_id": "owen_abstract09_fig_1",
  "text": "Figure 2: Not surprisingly, many of the component categories...",
  "metadata": {
    "chunk_type": "figure",
    "figure_description": "Figure showing: caption text only",
    "has_image": true
  }
}
```

### After (Proper AI Descriptions)
```json
{
  "chunk_id": "owen_abstract09_fig_1",
  "text": "Figure 2: An Abstraction Ladder produced...\n\nThe figure is an Abstraction Ladder diagram, a type of hierarchical diagram used in design thinking. The diagram shows a hierarchical structure starting with 'Chairs' at the top, branching down into categories like Living Room Chairs, Contemporary Seating, Period Replica Seating with specific examples like Eames Lounge Chair, Barcelona Chair...",
  "metadata": {
    "chunk_type": "figure",
    "figure_description": "Full 200+ word AI-generated description",
    "has_image": true,
    "owen_terms": ["Abstraction Ladder", "Structured Planning"],
    "figure_url": "https://project.supabase.co/storage/v1/..."
  }
}
```

**Embedding Quality:**
- ✅ Rich semantic content for similarity matching
- ✅ Owen terminology properly captured
- ✅ Visual concepts retrievable via text queries
- ✅ Figure-text relationships strengthened

---

## Production Readiness Checklist

### Infrastructure ✓
- [x] Supabase storage configured and working
- [x] Pinecone index exists and accessible
- [x] Voyage AI API key configured
- [x] Groq API key configured
- [x] Vision model updated to Llama 4 Scout

### Data Pipeline Status
- [x] PDF parsing complete (20 documents)
- [x] Figure extraction complete (56 figures)
- [x] Figures uploaded to Supabase
- [ ] Figure descriptions generated (NEEDS RE-RUN)
- [ ] Documents chunked with descriptions (NEEDS RE-RUN)
- [ ] Chunks indexed in Pinecone (NEEDS RE-RUN)

### Code Quality ✓
- [x] All PRD requirements implemented
- [x] No TODOs or incomplete implementations
- [x] Backward compatibility maintained (R2 → Supabase)
- [x] Error handling and rate limiting in place
- [x] Logging configured

### Testing
- [x] Vision model tested with sample figure
- [ ] End-to-end pipeline test (AFTER RE-RUN)
- [ ] Figure retrieval test (AFTER RE-RUN)
- [ ] Generation with figures test (AFTER RE-RUN)

---

## Commands to Run (In Order)

```bash
# 1. Regenerate descriptions (~5-10 min)
python regenerate_descriptions.py

# 2. Re-chunk documents (~1-2 min)
python scripts/chunk_documents.py

# 3. Re-index to Pinecone (~5-10 min)
python scripts/index_to_pinecone.py

# 4. Test retrieval
python scripts/test_figure_retrieval.py
```

**Total Time:** ~15-20 minutes for complete pipeline refresh

---

## Why This Architecture Is Production-Ready

### Separation of Concerns ✓
- Ingestion → Chunking → Indexing → Retrieval
- Each phase independent and re-runnable
- Failed phases don't corrupt earlier work

### Data Preservation ✓
- Original PDFs never modified
- Processed JSONs are source of truth
- Chunks regenerated from processed JSONs
- Index rebuildable from chunks

### Incremental Processing ✓
- Can re-run single documents
- Can skip phases (e.g., ingestion if done)
- Batch processing with progress bars
- Error recovery and logging

### Scalability ✓
- Current: 20 documents, ~900 chunks, 56 figures
- Pinecone free tier: 100K vectors (10% utilized)
- Voyage AI free tier: 200M tokens/month (0.1% utilized)
- Can scale to 200+ documents without infrastructure changes

### Quality Controls ✓
- Vision model versioning (Llama 4 Scout)
- Embedding model versioning (Voyage AI voyage-3)
- Sparse encoder serialization for consistency
- Metadata tracking for provenance

---

## Monitoring & Validation

### Key Metrics to Check
1. **Description Quality**: Spot-check 5-10 regenerated descriptions
2. **Chunk Count**: Should remain ~900 total (text + figures)
3. **Figure Chunk Count**: Should be 56 (one per figure)
4. **Pinecone Vectors**: Should be ~900 (match chunk count)
5. **Retrieval Precision**: Test queries should return relevant figures

### Validation Queries
```python
# Should retrieve Abstraction Ladder figures
"Show me examples of Abstraction Ladders"

# Should retrieve Information Structure diagrams
"What does an Information Structure look like?"

# Should retrieve concept generation matrices
"Explain the concept generation matrix"

# Should retrieve Design Factor examples
"Show me a completed Design Factor form"
```

---

## Timeline

| Phase | Duration | Can Run In Background? |
|-------|----------|----------------------|
| Description regeneration | 5-10 min | ❌ No (sequential API calls) |
| Chunking | 1-2 min | ✓ Yes |
| Indexing | 5-10 min | ✓ Yes |
| Validation | 2-3 min | ❌ No (manual testing) |
| **Total** | **15-20 min** | |

**Recommended:** Run during low-traffic period. Frontend remains functional during re-indexing (queries use old index until new one is ready).

---

## Rollback Plan (If Needed)

If re-indexing causes issues:

1. **Keep old index**: Pinecone supports multiple indexes
   - Create new index: `askchuck-v2`
   - Test with new index
   - Switch DNS/config when validated

2. **Revert config**:
   ```python
   # Temporarily use text-only retrieval
   skip_figures = True
   ```

3. **Debug offline**:
   - Chunks are saved locally in `data/chunks/`
   - Can inspect/validate before uploading

---

## Next Steps

1. **Run regeneration script** to update descriptions
2. **Re-chunk** with new descriptions
3. **Re-index** to Pinecone
4. **Validate** with test queries
5. **Document** any issues encountered
6. **Update PRD completion docs** when done

The architecture is solid and production-ready. This is just data refresh, not code changes.
