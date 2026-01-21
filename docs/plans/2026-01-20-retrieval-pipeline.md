# PRD-05: Retrieval Pipeline Implementation Plan

**Goal:** Build retrieval pipeline with Pinecone hybrid search + Cohere reranking

**Architecture:** Pinecone native hybrid (auto-fused dense+sparse) + Cohere cross-encoder

**Tech Stack:** Pinecone, Voyage AI, BM25 (from PRD-04), Cohere rerank-v3.0

---

## Task 1: Create Query Expansion Module

**Files:**
- Create: `src/retrieval/query_expansion.py`
- Create: `src/retrieval/__init__.py`

**Implementation:**
Expand queries with related Owen terminology using Groq LLM

**Steps:**
1. Create QueryExpander class
2. Use Owen glossary from src/utils/owen_glossary.py
3. Build prompt with glossary terms
4. Call Groq LLM for related terms
5. Append terms to original query
6. Make expansion optional (off by default)
7. Add logging for debug

**Verification:**
```python
from src.retrieval.query_expansion import QueryExpander
expander = QueryExpander()
expanded = expander.expand_query("How to document insights")
print(expanded)  # Should include "Design Factor" or similar
```

**Commit:** `feat: add query expansion with Owen terminology`

---

## Task 2: Create Pinecone Hybrid Retriever

**Files:**
- Create: `src/retrieval/pinecone_retriever.py`

**Implementation:**
Retrieve using Pinecone native hybrid search (dense + sparse)

**Steps:**
1. Create PineconeHybridRetriever class
2. Initialize with alpha parameter (default 0.5)
3. Load VoyageEmbedder from PRD-04
4. Load SparseEncoder from PRD-04
5. Implement retrieve() method
   - Generate dense vector with Voyage AI
   - Generate sparse vector with BM25
   - Query Pinecone with both vectors + alpha
6. Implement retrieve_with_expansion()
   - Detect high-scoring child chunks
   - Fetch parent chunks by parent_id
   - Add to candidate pool
7. Add convenience methods (retrieve_figures, retrieve_from_document)
8. Add fetch_neighbors() for contextual expansion
9. Handle metadata properly

**Verification:**
```python
from src.retrieval.pinecone_retriever import PineconeHybridRetriever
retriever = PineconeHybridRetriever(alpha=0.5)
results = retriever.retrieve("What is structured planning?", top_k=10)
print(f"Retrieved {len(results)} chunks")
print(f"Top result: {results[0]['chunk_id']} (score={results[0]['score']})")
```

**Commit:** `feat: add Pinecone hybrid retriever with parent expansion`

---

## Task 3: Create Cohere Reranker

**Files:**
- Create: `src/retrieval/reranker.py`

**Implementation:**
Rerank results using Cohere cross-encoder

**Steps:**
1. Create CohereReranker class
2. Initialize Cohere client (rerank-v3.0)
3. Implement rerank() method
   - Extract content from results
   - Truncate long documents (4000 char limit)
   - Call Cohere rerank API
   - Return reordered results with scores
4. Implement rerank_with_context() for conversational queries
5. Handle API errors gracefully (fallback to original order)
6. Add logging

**Verification:**
```python
from src.retrieval.reranker import CohereReranker
reranker = CohereReranker()
# Assume candidates is a list of results
reranked = reranker.rerank("structured planning", candidates, top_k=5)
print(f"Reranked {len(reranked)} results")
print(f"Top reranked: {reranked[0]['chunk_id']} (score={reranked[0]['rerank_score']})")
```

**Commit:** `feat: add Cohere cross-encoder reranker`

---

## Task 4: Create Complete Retrieval Pipeline

**Files:**
- Create: `src/retrieval/retrieval_pipeline.py`

**Implementation:**
Orchestrate the complete retrieval flow

**Steps:**
1. Create RetrievalPipeline class
2. Initialize with retriever, reranker, query_expander
3. Implement retrieve() method (main entry point)
   - Optional query expansion
   - Pinecone hybrid retrieval (initial_k=50)
   - Optional parent-child expansion
   - Cohere reranking (final_k=5)
   - Enrich results with display fields
4. Implement retrieve_with_figures()
   - Separate text and figure retrieval
   - Ensures figures included
5. Implement retrieve_with_neighbors()
   - Main results + neighbor chunks
6. Implement _enrich_results()
   - Add convenience fields (document_title, section, etc.)
   - Format owen_terms, figure_url properly
7. Add global instance pattern

**Verification:**
```python
from src.retrieval.retrieval_pipeline import RetrievalPipeline
pipeline = RetrievalPipeline()
results = pipeline.retrieve("What is structured planning?", top_k=5)
print(f"Final results: {len(results)}")
for i, r in enumerate(results, 1):
    print(f"{i}. {r['document_title']} - {r['chunk_id']}")
    print(f"   Score: {r.get('rerank_score', r.get('score'))}")
```

**Commit:** `feat: add complete retrieval pipeline`

---

## Task 5: Create CLI Test Script

**Files:**
- Create: `scripts/test_retrieval.py`

**Implementation:**
CLI for testing retrieval with sample queries

**Steps:**
1. Create test script with argparse
2. Add sample queries from PRD
   - Exact terminology queries
   - Semantic paraphrasing queries
   - Mixed queries
   - Figure queries
3. Options for:
   - Custom query input
   - Alpha tuning
   - With/without expansion
   - Top-k configuration
4. Display results with formatting
5. Show retrieval stats

**Verification:**
```bash
python scripts/test_retrieval.py --query "What is VTCON?" --alpha 0.3
python scripts/test_retrieval.py --query "How to categorize items" --alpha 0.7
python scripts/test_retrieval.py --test-all  # Run all sample queries
```

**Commit:** `feat: add retrieval testing CLI script`

---

## Task 6: Add Retrieval Verification

**Files:**
- Create: `scripts/verify_retrieval.py`

**Implementation:**
Comprehensive retrieval verification

**Steps:**
1. Create verification script
2. Test hybrid search at different alphas
3. Test parent-child expansion
4. Test figure filtering
5. Test document filtering
6. Test query expansion
7. Test reranking improvement
8. Report statistics and examples

**Verification:**
```bash
python scripts/verify_retrieval.py
# Should test all retrieval features and report pass/fail
```

**Commit:** `feat: add retrieval verification script`

---

## Task 7: Documentation

**Files:**
- Create: `docs/RETRIEVAL_COMPLETE.md`

**Content:**
- Component overview
- Architecture explanation
- Usage examples
- Configuration parameters
- Testing queries
- Performance notes
- Acceptance criteria checklist

**Commit:** `docs: add retrieval completion summary`

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| ✅ Pinecone hybrid query works | Test with dense+sparse vectors |
| ✅ Alpha parameter controls weighting | Compare results at 0.0, 0.5, 1.0 |
| ✅ Parent-child expansion | Verify parent chunks added to children |
| ✅ Cohere reranking | Compare order before/after rerank |
| ✅ Figure filtering | Retrieve only figure chunks |
| ✅ Document filtering | Retrieve from specific document |
| ✅ Query expansion | Check Owen terms added |
| ✅ Neighbor retrieval | Fetch sequential chunks |
| ✅ Error handling | Test API failures, verify fallbacks |
| ✅ CLI scripts | test_retrieval.py, verify_retrieval.py work |

---

## Notes

- **Pinecone alpha:** Default 0.5 (equal dense/sparse), tune via PRD-08
- **Initial k:** Retrieve 50 candidates for good recall
- **Final k:** Rerank to top 5 for precision
- **Parent expansion:** Default enabled, threshold 0.7 score
- **Query expansion:** Default disabled (add opt-in for exploration)
- **Sparse encoder:** Load from PRD-04 saved encoder
- **Cohere free tier:** 1000 requests/month (sufficient for dev)

---

## Dependencies

**From PRD-04:**
- `src/indexing/embeddings.py` - VoyageEmbedder
- `src/indexing/sparse_encoder.py` - SparseEncoder (load saved encoder)
- `src/indexing/vector_store.py` - PineconeIndexManager
- `data/sparse_encoder.pkl` - Saved BM25 encoder

**From PRD-03:**
- `src/utils/owen_glossary.py` - Owen terminology

**New dependencies:**
- `cohere` package (already in requirements.txt)
