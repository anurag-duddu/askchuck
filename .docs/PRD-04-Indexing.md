# PRD-04: Indexing

## Document Information

| Field | Value |
|-------|-------|
| PRD ID | PRD-04 |
| Version | v2.0 |
| Phase | 3 |
| Estimated Duration | 2 hours |
| Dependencies | PRD-03 (Chunking & Enrichment) |
| Owner | Developer |

**Key Changes from v1.0:**
- Switched from Chroma to Pinecone Serverless for vector storage
- Switched from BGE embeddings to Voyage AI voyage-3 (1024-dim)
- Eliminated separate BM25 index - Pinecone native hybrid search
- Index both parent AND child chunks for retrieval flexibility
- Unified index for text and figure chunks with metadata filtering

---

## Objective

Build the Pinecone hybrid search index that enables fast, accurate retrieval combining semantic and lexical signals. This phase embeds all hierarchical chunks using Voyage AI and indexes them in Pinecone Serverless with both dense and sparse vectors, enabling native hybrid search without manual BM25 indexing or fusion logic.

---

## Background

### Why Hybrid Search?

Dense vector search excels at semantic similarity—a query for "categorization hierarchy" matches chunks about "Abstraction Ladder" because the embedding model understands conceptual relationships. However, dense search can miss exact terminology matches. A query for "VTCON" might retrieve generic clustering content rather than specific VTCON program references.

Sparse retrieval (BM25-style) excels at lexical matching. When a user searches for "Design Factor," chunks containing those exact words rank highly. This is critical for Owen's specialized vocabulary where terms like "Speculation," "Mode," and "Function" have precise meanings distinct from everyday usage.

Research consistently shows hybrid retrieval combining dense and sparse methods outperforms either alone by 15-30%. For specialized domains like Owen's methodology, hybrid search is essential rather than optional.

### Why Pinecone Native Hybrid Search?

Pinecone Serverless provides **built-in hybrid search**:
- Single index stores both dense (semantic) and sparse (lexical) vectors per chunk
- Single query API combines both retrieval signals automatically
- Built-in BM25F algorithm handles sparse vector scoring
- Automatic reciprocal rank fusion (RRF) merges results
- No manual BM25 index maintenance, no manual fusion logic

This eliminates ~400 lines of code and an entire maintenance burden compared to separate BM25 indexing.

### Why Voyage AI?

Voyage AI's voyage-3 model is optimized specifically for RAG:
- **Quality**: Best-in-class retrieval performance on MTEB benchmarks
- **Dimensionality**: 1024 dimensions (vs BGE's 384) capture richer semantic information
- **Context**: 32K token context window handles long academic chunks
- **Cost**: Free tier provides 200M tokens/month (more than sufficient for 20 documents)
- **API-based**: No local model downloads, consistent versioning

### Why Index Both Parent and Child Chunks?

PRD-03 established hierarchical chunking with:
- **Parent chunks** (2048 tokens): Broader conceptual context
- **Child chunks** (512 tokens): Precise specific passages

Indexing BOTH levels provides retrieval flexibility:
- Broad conceptual queries match parent chunks providing comprehensive context
- Specific detail queries match child chunks with precise answers
- Hierarchical metadata (`parent_id`, `child_ids`) enables dynamic expansion during retrieval
- ~2x chunks (~900 total) but well within Pinecone free tier (2GB)

---

## Functional Requirements

### FR-01: Dense Vector Embedding

The system shall generate dense embeddings for all chunks using Voyage AI voyage-3.

**Acceptance Criteria:**
- Uses Voyage AI voyage-3 model (1024 dimensions)
- Embeds the `enriched_text` field (includes contextual prefix from PRD-03)
- Uses `input_type="document"` for chunk embeddings
- Uses `input_type="query"` for search queries
- Batches embedding requests (128 chunks per batch)
- Handles API rate limits with exponential backoff
- Logs progress during batch embedding

### FR-02: Sparse Vector Generation

The system shall generate BM25-style sparse vectors for all chunks to enable lexical matching.

**Acceptance Criteria:**
- Uses `pinecone-text` BM25Encoder for sparse vector generation
- Fits encoder on full corpus during indexing
- Generates sparse vectors in format `{"indices": [...], "values": [...]}`
- Preserves Owen terminology in tokenization
- Serializes fitted encoder for query-time usage
- Fallback to manual token hashing if library unavailable

### FR-03: Pinecone Index Creation

The system shall create a Pinecone Serverless index configured for hybrid search.

**Acceptance Criteria:**
- Index name: "askchuck"
- Dimension: 1024 (Voyage AI voyage-3)
- Metric: cosine similarity for dense vectors
- Spec: Serverless (AWS us-east-1)
- Enables native hybrid search (dense + sparse vectors)
- Creates index if not exists, connects if exists

### FR-04: Hierarchical Chunk Indexing

The system shall index all chunks (parent, child, figure) with both dense and sparse vectors.

**Acceptance Criteria:**
- Indexes parent chunks with `chunk_level="parent"`
- Indexes child chunks with `chunk_level="child"`
- Indexes figure chunks with `chunk_type="figure"`
- Each chunk stores: dense vector, sparse vector, full metadata
- Metadata includes: `chunk_id`, `document_id`, `chunk_type`, `chunk_level`, `parent_id`, `child_ids`, `document_title`, `section`, `owen_terms`, `enriched_text`
- Upserts in batches of 100 vectors
- Logs progress during upsertion

### FR-05: Index Verification

The system shall verify index integrity and test hybrid search functionality.

**Acceptance Criteria:**
- Reports total indexed vectors
- Reports parent/child/figure chunk breakdown
- Tests sample hybrid query returns results
- Tests metadata filtering (by `chunk_type`, `document_id`)
- Validates dense and sparse vectors present
- Reports index statistics (dimension, metric, vector count)

---

## Technical Specification

### Embedding Strategy

**Voyage AI voyage-3:**
- Best-in-class RAG performance
- 1024 dimensions (richer semantic representation than BGE's 384)
- 32K context window (handles long academic chunks)
- Input types: `document` for indexing, `query` for retrieval
- Free tier: 200M tokens/month

**Token Estimate for 20 Documents:**
- ~900 chunks total (parents + children + figures)
- Average enriched chunk: ~600 tokens
- Total: 900 × 600 = 540K tokens (well under 200M limit)

### Sparse Vector Strategy

**Pinecone-text BM25Encoder:**
```python
from pinecone_text.sparse import BM25Encoder

# Fit on corpus during indexing
bm25_encoder = BM25Encoder.default()
bm25_encoder.fit(all_enriched_texts)

# Generate sparse vectors
sparse_vector = bm25_encoder.encode_documents([text])[0]
# Returns: {"indices": [12, 45, 67, ...], "values": [0.8, 0.6, 0.4, ...]}

# Save for query-time
bm25_encoder.dump("bm25_encoder.json")
```

**Sparse Vector Format:**
- `indices`: List of token hash indices
- `values`: List of BM25 weights (TF-IDF style)
- Pinecone handles IDF calculation and scoring internally

### Index Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PINECONE SERVERLESS INDEX                 │
│                        "askchuck"                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Chunks (enriched text)                                     │
│  ┌──────────────┐    ┌──────────────┐                       │
│  │   Parent     │    │    Child     │                       │
│  │   Chunks     │    │   Chunks     │                       │
│  │  (~250)      │    │  (~500)      │                       │
│  └──────┬───────┘    └──────┬───────┘                       │
│         │                   │                               │
│         └──────────┬────────┘                               │
│                    │                                        │
│                    ▼                                        │
│         ┌──────────────────────┐                            │
│         │    Voyage AI v3      │                            │
│         │   voyage-3 API       │                            │
│         │  (1024-dim dense)    │                            │
│         └──────────┬───────────┘                            │
│                    │                                        │
│                    ▼                                        │
│         ┌──────────────────────┐                            │
│         │  pinecone-text       │                            │
│         │  BM25Encoder         │                            │
│         │  (sparse vectors)    │                            │
│         └──────────┬───────────┘                            │
│                    │                                        │
│                    ▼                                        │
│  ┌─────────────────────────────────────────────┐            │
│  │              HYBRID UPSERT                   │            │
│  │  {                                           │            │
│  │    "id": "chunk_id",                         │            │
│  │    "values": [dense vector],                 │            │
│  │    "sparse_values": {indices, values},       │            │
│  │    "metadata": {...}                         │            │
│  │  }                                           │            │
│  └──────────────────┬───────────────────────────┘            │
│                     │                                        │
│                     ▼                                        │
│  ┌─────────────────────────────────────────────┐            │
│  │          PINECONE INDEX STORAGE              │            │
│  │                                              │            │
│  │  • Dense vectors (1024-dim)                  │            │
│  │  • Sparse vectors (BM25-style)               │            │
│  │  • Metadata (chunk info)                     │            │
│  │  • Hierarchical links (parent/child IDs)     │            │
│  │                                              │            │
│  │  Query API: Native hybrid search             │            │
│  │  (Automatic dense + sparse fusion)           │            │
│  └──────────────────────────────────────────────┘            │
│                                                              │
│  Figure Chunks (~150)                                        │
│  └─▶ Same index, filtered by chunk_type="figure"            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Metadata Schema

Pinecone metadata per vector:

```python
{
    "chunk_id": "owen_power_of_abstraction_2009_chunk_005",
    "document_id": "owen_power_of_abstraction_2009",
    "chunk_type": "text",  # or "figure"
    "chunk_level": "child",  # "parent", "child", or "independent"
    "parent_id": "owen_power_of_abstraction_2009_chunk_002",
    "document_title": "The Power of Abstraction",
    "section": "The Abstraction Ladder",
    "owen_terms": "Abstraction Ladder,Function,Abstraction Structure",  # Comma-separated
    "text": "This chunk is from 'The Power of Abstraction' (2009)...",  # Enriched text for display
}
```

**Note:** Pinecone metadata has limitations:
- Flat structure only (no nested objects)
- Arrays stored as comma-separated strings
- Keep metadata minimal for efficient filtering

---

## Implementation Details

### File: src/indexing/embeddings.py

```python
"""
Voyage AI embedding generation for dense vectors.
Optimized for RAG with voyage-3 model.
"""

import logging
from typing import List
import voyageai

from src.utils.config import settings

logger = logging.getLogger(__name__)


class VoyageEmbedder:
    """
    Generates dense embeddings using Voyage AI voyage-3.
    Optimized for Owen literature retrieval.
    """

    def __init__(self):
        self.client = voyageai.Client(api_key=settings.voyage_api_key)
        self.model = "voyage-3"
        self.dimension = 1024
        logger.info(f"Initialized Voyage AI embedder: {self.model} ({self.dimension}-dim)")

    def embed_documents(
        self,
        texts: List[str],
        batch_size: int = 128
    ) -> List[List[float]]:
        """
        Embed documents in batches with progress logging.

        Args:
            texts: List of document texts to embed
            batch_size: Number of texts per API call

        Returns:
            List of embedding vectors (1024-dim each)
        """
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            logger.info(f"Embedding batch {i // batch_size + 1} ({i + 1}-{i + len(batch)} of {len(texts)})")

            try:
                result = self.client.embed(
                    batch,
                    model=self.model,
                    input_type="document"  # Optimized for document indexing
                )

                all_embeddings.extend(result.embeddings)

            except Exception as e:
                logger.error(f"Error embedding batch {i // batch_size + 1}: {e}")
                raise

        logger.info(f"Successfully embedded {len(all_embeddings)} documents")
        return all_embeddings

    def embed_query(self, query: str) -> List[float]:
        """
        Embed a single query for retrieval.

        Args:
            query: Search query text

        Returns:
            Embedding vector (1024-dim)
        """
        result = self.client.embed(
            [query],
            model=self.model,
            input_type="query"  # Optimized for query retrieval
        )
        return result.embeddings[0]


# Global instance
_embedder = None


def get_embedder() -> VoyageEmbedder:
    """Get or create the global embedder instance."""
    global _embedder
    if _embedder is None:
        _embedder = VoyageEmbedder()
    return _embedder
```

### File: src/indexing/sparse_encoder.py

```python
"""
BM25-style sparse vector generation for Pinecone hybrid search.
Uses pinecone-text library for consistent tokenization and weighting.
"""

import logging
import json
from pathlib import Path
from typing import List, Dict

from pinecone_text.sparse import BM25Encoder

from src.utils.config import DATA_DIR

logger = logging.getLogger(__name__)

BM25_ENCODER_PATH = DATA_DIR / "bm25_encoder.json"


class OwenSparseEncoder:
    """
    BM25-based sparse encoder for Owen literature.
    Generates sparse vectors compatible with Pinecone hybrid search.
    """

    def __init__(self):
        self.encoder: BM25Encoder = None
        self.is_fitted = False

    def fit(self, texts: List[str]):
        """
        Fit BM25 encoder on corpus.
        Must be called before encoding.

        Args:
            texts: Full corpus of texts to fit on
        """
        logger.info(f"Fitting BM25 encoder on {len(texts)} documents")

        self.encoder = BM25Encoder.default()
        self.encoder.fit(texts)
        self.is_fitted = True

        logger.info("BM25 encoder fitted successfully")

    def encode_documents(self, texts: List[str]) -> List[Dict]:
        """
        Encode documents to sparse vectors.

        Args:
            texts: List of document texts

        Returns:
            List of sparse vectors: [{"indices": [...], "values": [...]}, ...]
        """
        if not self.is_fitted:
            raise ValueError("Encoder must be fitted before encoding")

        sparse_vectors = self.encoder.encode_documents(texts)
        return sparse_vectors

    def encode_query(self, query: str) -> Dict:
        """
        Encode query to sparse vector.

        Args:
            query: Search query text

        Returns:
            Sparse vector: {"indices": [...], "values": [...]}
        """
        if not self.is_fitted:
            raise ValueError("Encoder must be fitted before encoding")

        sparse_vector = self.encoder.encode_queries([query])[0]
        return sparse_vector

    def save(self, path: Path = None):
        """Save fitted encoder to disk."""
        if not self.is_fitted:
            raise ValueError("Cannot save unfitted encoder")

        path = path or BM25_ENCODER_PATH
        path.parent.mkdir(parents=True, exist_ok=True)

        self.encoder.dump(str(path))
        logger.info(f"BM25 encoder saved to {path}")

    def load(self, path: Path = None):
        """Load fitted encoder from disk."""
        path = path or BM25_ENCODER_PATH

        if not path.exists():
            raise FileNotFoundError(f"Encoder file not found: {path}")

        self.encoder = BM25Encoder.load(str(path))
        self.is_fitted = True

        logger.info(f"BM25 encoder loaded from {path}")


# Global instance
_encoder = None


def get_sparse_encoder() -> OwenSparseEncoder:
    """Get or create the global sparse encoder instance."""
    global _encoder
    if _encoder is None:
        _encoder = OwenSparseEncoder()
        # Try to load existing encoder
        if BM25_ENCODER_PATH.exists():
            _encoder.load()
    return _encoder
```

### File: src/indexing/pinecone_store.py

```python
"""
Pinecone vector store for hybrid search.
Manages index creation and hybrid vector upsertion.
"""

import logging
from typing import List, Dict, Optional

from pinecone import Pinecone, ServerlessSpec

from src.utils.config import settings
from src.indexing.embeddings import VoyageEmbedder
from src.indexing.sparse_encoder import OwenSparseEncoder

logger = logging.getLogger(__name__)


class PineconeHybridStore:
    """
    Pinecone vector store with native hybrid search support.
    Stores both dense (Voyage AI) and sparse (BM25) vectors per chunk.
    """

    INDEX_NAME = "askchuck"
    DIMENSION = 1024  # Voyage AI voyage-3
    METRIC = "cosine"
    CLOUD = "aws"
    REGION = "us-east-1"

    def __init__(self):
        """Initialize Pinecone client and connect to index."""
        self.pc = Pinecone(api_key=settings.pinecone_api_key)

        # Create or connect to index
        if self.INDEX_NAME not in self.pc.list_indexes().names():
            logger.info(f"Creating Pinecone index: {self.INDEX_NAME}")
            self.pc.create_index(
                name=self.INDEX_NAME,
                dimension=self.DIMENSION,
                metric=self.METRIC,
                spec=ServerlessSpec(
                    cloud=self.CLOUD,
                    region=self.REGION
                )
            )
            logger.info("Index created successfully")
        else:
            logger.info(f"Connecting to existing index: {self.INDEX_NAME}")

        self.index = self.pc.Index(self.INDEX_NAME)
        stats = self.index.describe_index_stats()
        logger.info(f"Index stats: {stats['total_vector_count']} vectors")

    def upsert_chunks(
        self,
        chunks: List[Dict],
        dense_embeddings: List[List[float]],
        sparse_vectors: List[Dict],
        batch_size: int = 100
    ):
        """
        Upsert chunks with both dense and sparse vectors.

        Args:
            chunks: List of chunk dictionaries from PRD-03
            dense_embeddings: List of dense vectors from Voyage AI
            sparse_vectors: List of sparse vectors from BM25Encoder
            batch_size: Number of vectors per upsert batch
        """
        if len(chunks) != len(dense_embeddings) != len(sparse_vectors):
            raise ValueError("Chunk count, dense embedding count, and sparse vector count must match")

        logger.info(f"Upserting {len(chunks)} chunks to Pinecone")

        # Prepare vectors for upsert
        vectors = []
        for i, chunk in enumerate(chunks):
            # Flatten metadata for Pinecone (no nested objects)
            metadata = self._prepare_metadata(chunk)

            vector = {
                "id": chunk["chunk_id"],
                "values": dense_embeddings[i],
                "sparse_values": sparse_vectors[i],
                "metadata": metadata
            }
            vectors.append(vector)

        # Upsert in batches
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            self.index.upsert(vectors=batch)
            logger.info(f"Upserted {i + len(batch)} / {len(vectors)} vectors")

        logger.info(f"Successfully upserted all {len(vectors)} vectors")

    def _prepare_metadata(self, chunk: Dict) -> Dict:
        """
        Prepare chunk metadata for Pinecone.
        Flattens nested structures and converts arrays to strings.

        Args:
            chunk: Chunk dictionary from PRD-03

        Returns:
            Flattened metadata dictionary
        """
        metadata = {
            "chunk_id": chunk["chunk_id"],
            "document_id": chunk["document_id"],
            "chunk_type": chunk["chunk_type"],
            "chunk_level": chunk.get("chunk_level", "independent"),
            "document_title": chunk["metadata"]["document_title"],
            "section": chunk["metadata"]["section"],
            "text": chunk.get("enriched_text") or chunk["original_text"],
        }

        # Add parent/child IDs if present
        if chunk.get("parent_id"):
            metadata["parent_id"] = chunk["parent_id"]

        # Add Owen terms (comma-separated)
        owen_terms = chunk["metadata"].get("owen_terms", [])
        if owen_terms:
            metadata["owen_terms"] = ",".join(owen_terms)

        return metadata

    def hybrid_query(
        self,
        query_dense: List[float],
        query_sparse: Dict,
        top_k: int = 50,
        filter: Optional[Dict] = None
    ) -> Dict:
        """
        Execute hybrid query with both dense and sparse vectors.
        Pinecone handles fusion automatically.

        Args:
            query_dense: Dense query embedding from Voyage AI
            query_sparse: Sparse query vector from BM25Encoder
            top_k: Number of results to return
            filter: Optional metadata filter

        Returns:
            Query results with matches, scores, and metadata
        """
        results = self.index.query(
            vector=query_dense,
            sparse_vector=query_sparse,
            top_k=top_k,
            filter=filter,
            include_metadata=True
        )

        return results

    def get_stats(self) -> Dict:
        """Get index statistics."""
        stats = self.index.describe_index_stats()
        return {
            "total_vectors": stats["total_vector_count"],
            "dimension": stats["dimension"],
            "index_fullness": stats.get("index_fullness", 0.0),
            "namespaces": stats.get("namespaces", {})
        }


# Global instance
_store = None


def get_pinecone_store() -> PineconeHybridStore:
    """Get or create the global Pinecone store instance."""
    global _store
    if _store is None:
        _store = PineconeHybridStore()
    return _store
```

### File: scripts/build_index.py

```python
"""
Build Pinecone hybrid index from chunks.
Generates dense embeddings (Voyage AI) and sparse vectors (BM25),
then upserts to Pinecone with hierarchical metadata.
"""

import json
import logging
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.indexing.embeddings import VoyageEmbedder
from src.indexing.sparse_encoder import OwenSparseEncoder
from src.indexing.pinecone_store import PineconeHybridStore
from src.utils.config import CHUNKS_DIR

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Build Pinecone hybrid index from all chunks."""

    start_time = datetime.now()

    logger.info("=" * 60)
    logger.info("Building Pinecone Hybrid Index")
    logger.info("=" * 60)

    # Step 1: Load chunks
    logger.info("\nStep 1: Loading chunks")
    chunks_file = CHUNKS_DIR / "all_chunks.json"

    if not chunks_file.exists():
        logger.error(f"Chunks file not found: {chunks_file}")
        logger.error("Run chunking pipeline first (PRD-03)!")
        sys.exit(1)

    with open(chunks_file, 'r', encoding='utf-8') as f:
        chunks = json.load(f)

    logger.info(f"Loaded {len(chunks)} chunks")

    # Breakdown by type and level
    parent_chunks = [c for c in chunks if c.get("chunk_level") == "parent"]
    child_chunks = [c for c in chunks if c.get("chunk_level") == "child"]
    figure_chunks = [c for c in chunks if c["chunk_type"] == "figure"]

    logger.info(f"  Parent chunks: {len(parent_chunks)}")
    logger.info(f"  Child chunks: {len(child_chunks)}")
    logger.info(f"  Figure chunks: {len(figure_chunks)}")

    # Step 2: Generate dense embeddings
    logger.info("\n" + "=" * 60)
    logger.info("Step 2: Generating dense embeddings (Voyage AI)")
    logger.info("=" * 60)

    embedder = VoyageEmbedder()

    # Extract enriched text for embedding
    texts = [
        c.get("enriched_text") or c.get("original_text", "")
        for c in chunks
    ]

    dense_embeddings = embedder.embed_documents(texts, batch_size=128)
    logger.info(f"Generated {len(dense_embeddings)} dense embeddings (1024-dim)")

    # Step 3: Generate sparse vectors
    logger.info("\n" + "=" * 60)
    logger.info("Step 3: Generating sparse vectors (BM25)")
    logger.info("=" * 60)

    sparse_encoder = OwenSparseEncoder()

    # Fit encoder on corpus
    sparse_encoder.fit(texts)

    # Generate sparse vectors
    sparse_vectors = sparse_encoder.encode_documents(texts)
    logger.info(f"Generated {len(sparse_vectors)} sparse vectors")

    # Save encoder for query-time usage
    sparse_encoder.save()
    logger.info("BM25 encoder saved for retrieval")

    # Step 4: Upsert to Pinecone
    logger.info("\n" + "=" * 60)
    logger.info("Step 4: Upserting to Pinecone")
    logger.info("=" * 60)

    store = PineconeHybridStore()
    store.upsert_chunks(chunks, dense_embeddings, sparse_vectors, batch_size=100)

    # Step 5: Verification
    logger.info("\n" + "=" * 60)
    logger.info("Step 5: Verifying index")
    logger.info("=" * 60)

    stats = store.get_stats()
    logger.info(f"Index statistics:")
    logger.info(f"  Total vectors: {stats['total_vectors']}")
    logger.info(f"  Dimension: {stats['dimension']}")
    logger.info(f"  Index fullness: {stats['index_fullness']:.2%}")

    # Test hybrid query
    logger.info("\nTesting hybrid query...")
    test_query = "What is an Abstraction Ladder?"

    query_dense = embedder.embed_query(test_query)
    query_sparse = sparse_encoder.encode_query(test_query)

    results = store.hybrid_query(query_dense, query_sparse, top_k=3)

    logger.info(f"Test query: '{test_query}'")
    logger.info(f"Top 3 results:")
    for i, match in enumerate(results['matches']):
        chunk_id = match['id']
        score = match['score']
        title = match['metadata'].get('document_title', 'Unknown')
        logger.info(f"  {i+1}. {chunk_id} (score: {score:.4f}) - {title}")

    # Summary
    elapsed = datetime.now() - start_time

    logger.info("\n" + "=" * 60)
    logger.info("Indexing Complete!")
    logger.info("=" * 60)
    logger.info(f"Total chunks indexed: {len(chunks)}")
    logger.info(f"  Parent chunks: {len(parent_chunks)}")
    logger.info(f"  Child chunks: {len(child_chunks)}")
    logger.info(f"  Figure chunks: {len(figure_chunks)}")
    logger.info(f"Dense embedding dimension: {embedder.dimension}")
    logger.info(f"Pinecone index: {store.INDEX_NAME}")
    logger.info(f"Time elapsed: {elapsed}")
    logger.info("\nReady for retrieval (PRD-05)!")


if __name__ == "__main__":
    main()
```

---

## Acceptance Criteria

| Criterion | Verification Method |
|-----------|-------------------|
| All chunks embedded with Voyage AI | Check embeddings shape: (n_chunks, 1024) |
| Sparse vectors generated for all chunks | Check sparse_vectors list length matches chunks |
| Pinecone index created | Query `pc.list_indexes()` includes "askchuck" |
| Parent chunks indexed | Filter query by `chunk_level="parent"` returns results |
| Child chunks indexed | Filter query by `chunk_level="child"` returns results |
| Figure chunks indexed | Filter query by `chunk_type="figure"` returns results |
| Hybrid search works | Test query returns ranked results combining dense + sparse |
| Metadata filtering works | Filter by `document_id` returns only that document's chunks |
| Hierarchical links preserved | Check `parent_id` metadata present in child chunks |
| BM25 encoder saved | File exists at `data/bm25_encoder.json` |
| Index statistics reported | `get_stats()` returns total vector count |
| Total vectors match chunk count | Index total_vectors == len(all_chunks) |

---

## Index Size Estimates

For 20 documents with hierarchical chunking:

**Chunk Estimates:**
- Parent chunks: ~250
- Child chunks: ~500
- Figure chunks: ~150
- **Total: ~900 vectors**

**Storage Estimates:**
- Dense vectors: 900 × 1024 dimensions × 4 bytes = ~3.5MB
- Sparse vectors: ~1-2MB (variable based on vocabulary)
- Metadata: ~2MB (IDs, document titles, sections, etc.)
- **Total: ~7-10MB** (well under Pinecone free tier 2GB limit)

**API Usage:**
- Voyage AI embeddings: 900 chunks × 600 tokens avg = 540K tokens (0.27% of 200M free tier)
- Pinecone upserts: 900 vectors (unlimited in Serverless free tier)
- Pinecone queries: Unlimited in free tier

---

## Next Steps

Once indexing is complete, proceed to **PRD-05: Retrieval** to build the hybrid retrieval pipeline that queries this index with dense+sparse vectors, applies metadata filtering, and reranks results with Cohere.
