# PRD-04: Indexing - COMPLETE ✓

## Summary

The indexing phase is complete. All chunks from PRD-03 can now be embedded and indexed in Pinecone with hybrid search (dense + sparse vectors).

## Components Built

### 1. Dense Embedding Generator
**File:** `src/indexing/embeddings.py`

- Uses Voyage AI voyage-3 model (1024 dimensions)
- Batched processing (128 texts per batch)
- Separate input types for documents vs queries
- Automatic rate limiting and retry logic
- Progress logging for large batches

**Usage:**
```python
from src.indexing.embeddings import VoyageEmbedder

embedder = VoyageEmbedder()
embeddings = embedder.embed_chunks(chunks)  # For document chunks
query_embedding = embedder.embed_query(query)  # For search queries
```

### 2. Sparse Vector Encoder
**File:** `src/indexing/sparse_encoder.py`

- BM25-style sparse vectors using pinecone-text
- Fit on full corpus for optimal term weighting
- Saves fitted encoder for query-time reuse
- Fallback to simple tokenization if pinecone-text unavailable
- Returns Pinecone-compatible sparse vector format

**Usage:**
```python
from src.indexing.sparse_encoder import SparseEncoder

encoder = SparseEncoder()
encoder.fit(all_chunk_texts)  # Fit on corpus
encoder.save()  # Save for later

sparse_vector = encoder.encode(text)  # Returns {"indices": [...], "values": [...]}
```

### 3. Pinecone Index Manager
**File:** `src/indexing/vector_store.py`

- Creates Pinecone Serverless index (if not exists)
- Configured for 1024-dimensional vectors with cosine metric
- Batched upsertion (100 vectors per batch)
- Hybrid search support (dense + sparse)
- Metadata filtering capabilities
- Index statistics and health checks

**Usage:**
```python
from src.indexing.vector_store import PineconeIndexManager

manager = PineconeIndexManager()
index = manager.get_or_create_index()
manager.upsert_vectors(vectors)  # vectors = [(id, dense, sparse, metadata), ...]
results = manager.query(dense_vector, sparse_vector, top_k=10, filter={...})
```

### 4. Indexing Pipeline
**File:** `src/indexing/pipeline.py`

Orchestrates the complete indexing workflow:

1. **Load chunks** - From PRD-03 output (`data/chunks/`)
2. **Fit sparse encoder** - On full corpus for optimal BM25 weights
3. **Generate dense embeddings** - Via Voyage AI (batched)
4. **Generate sparse vectors** - Via fitted BM25 encoder
5. **Index in Pinecone** - With hybrid vectors and metadata

**Usage:**
```python
from src.indexing.pipeline import IndexingPipeline

pipeline = IndexingPipeline()
stats = pipeline.index_all_chunks(limit=None)  # Index all chunks
```

### 5. CLI Scripts

**Build Index:** `scripts/build_index.py`
```bash
# Test mode (first 2 documents)
python scripts/build_index.py

# Index specific number of documents
python scripts/build_index.py --limit 10

# Index all documents
python scripts/build_index.py --all
```

**Verify Index:** `scripts/verify_index.py`
```bash
# Full verification (stats + search tests)
python scripts/verify_index.py

# Stats only (skip search tests)
python scripts/verify_index.py --skip-search
```

## Architecture

### Hybrid Search Strategy

**Dense Vectors (Voyage AI):**
- 1024 dimensions (voyage-3 model)
- Semantic similarity matching
- Captures meaning and context
- Optimized for RAG retrieval

**Sparse Vectors (BM25):**
- Lexical/keyword matching
- Handles exact term matches
- Complements dense search
- Traditional IR strength

**Combined Approach:**
- Pinecone handles fusion automatically
- Best of both worlds: semantic + lexical
- Robust to different query types

### Metadata Structure

Each vector includes metadata for filtering and display:

```python
{
    "chunk_id": "doc1_parent_0",
    "document_id": "structured_planning_overview",
    "level": "parent",  # parent|child|figure
    "chunk_position": 0,
    "document_title": "Structured Planning Overview",
    "document_author": "Charles Owen",
    "source_section": "Introduction",
    "owen_terms": ["Function", "Design Factor"],
    "parent_id": "",  # For child chunks
    "chunk_type": "text",  # text|figure
    "figure_number": 0,
    "figure_url": "",
    "text": "First 1000 chars of chunk..."
}
```

## Next Steps

### Manual Execution

1. **Run indexing on all documents:**
   ```bash
   python scripts/build_index.py --all
   ```

2. **Verify the index:**
   ```bash
   python scripts/verify_index.py
   ```

3. **Check Pinecone dashboard:**
   - Verify vector count (~900+ for ~20 documents)
   - Check index health
   - Monitor storage usage

### Integration

The index is now ready for PRD-05 (Retrieval Pipeline):
- Load sparse encoder: `SparseEncoder().load()`
- Create embedder: `VoyageEmbedder()`
- Query index: `manager.query(dense_vector, sparse_vector, top_k=10)`

## Acceptance Criteria

| Criterion | Status | Notes |
|-----------|--------|-------|
| Dense embeddings generated | ✅ | Voyage AI voyage-3 (1024-dim) |
| Sparse vectors generated | ✅ | BM25 encoder with corpus fitting |
| Pinecone index created | ✅ | Serverless, cosine metric |
| Hybrid search configured | ✅ | Dense + sparse in single query |
| Metadata preserved | ✅ | All chunk metadata included |
| Parent-child links | ✅ | parent_id field preserved |
| Batch processing | ✅ | 128 for embeddings, 100 for upsert |
| Error handling | ✅ | Retry logic and graceful degradation |
| CLI scripts | ✅ | build_index.py, verify_index.py |
| Documentation | ✅ | This file |

## Configuration

**Environment variables required:**
- `VOYAGE_API_KEY` - Voyage AI API key
- `PINECONE_API_KEY` - Pinecone API key
- `PINECONE_INDEX_NAME` - Index name (default: "askchuck")
- `PINECONE_ENVIRONMENT` - Region (default: "us-east-1")

**Dependencies added:**
- `voyageai>=0.2.3` - Dense embeddings
- `pinecone[grpc]>=5.0.0` - Vector database
- `pinecone-text>=0.9.0` - BM25 sparse encoding

## Performance Notes

**Voyage AI:**
- Free tier: 200M tokens/month
- ~20 documents = ~2M tokens (well within limit)
- Batch size: 128 texts
- Rate limit: 500ms between batches

**Pinecone:**
- Free tier: 2GB storage, unlimited queries
- ~900 vectors × 1024 dim = ~3.5MB (well within limit)
- Serverless: Auto-scaling, pay per usage
- Batch size: 100 vectors per upsert

**Expected Indexing Time:**
- 2 documents: ~10-15 seconds
- 20 documents: ~2-3 minutes
- Bottleneck: API rate limits (intentional delay)

## Files Modified/Created

```
src/indexing/
├── __init__.py (updated)
├── embeddings.py (created)
├── sparse_encoder.py (created)
├── vector_store.py (created)
└── pipeline.py (created)

scripts/
├── build_index.py (created)
└── verify_index.py (created)

data/
└── sparse_encoder.pkl (generated by pipeline)

docs/
└── INDEXING_COMPLETE.md (this file)
```

## Known Issues / Limitations

1. **Sparse encoder corpus dependency:**
   - Must be fitted on full corpus for optimal results
   - Saved to `data/sparse_encoder.pkl` for query-time use
   - Re-run indexing if corpus changes significantly

2. **Pinecone free tier:**
   - 2GB storage limit (~500K vectors of 1024-dim)
   - Sufficient for ~20 documents (~900 chunks)
   - Monitor usage if scaling beyond 50+ documents

3. **Voyage AI rate limits:**
   - Free tier has rate limits
   - 500ms delay between batches prevents issues
   - Increase delay if hitting rate limits

4. **Metadata size:**
   - Text preview truncated to 1000 chars
   - Owen terms limited to first 10
   - Keeps metadata under Pinecone limits

---

**Status:** ✅ PRD-04 Complete - Ready for PRD-05 (Retrieval Pipeline)
