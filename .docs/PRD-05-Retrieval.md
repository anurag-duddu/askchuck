# PRD-05: Retrieval Pipeline

## Document Information

| Field | Value |
|-------|-------|
| PRD ID | PRD-05 |
| Version | v2.0 |
| Phase | 4 |
| Estimated Duration | 2 hours |
| Dependencies | PRD-04 (Indexing) |
| Owner | Developer |

**Key Changes from v1.0:**
- Switched from Chroma+BM25 dual retrieval to Pinecone native hybrid search
- Eliminated manual RRF fusion (~100 LOC) - Pinecone handles this automatically
- Added hierarchical parent-child expansion logic
- Added neighbor chunk retrieval for contextual expansion
- Updated from Supabase to Cloudflare R2 for figure URLs
- Uses Voyage AI embeddings and BM25Encoder sparse vectors from PRD-04

---

## Objective

Build the retrieval pipeline that queries the Pinecone hybrid index and reranks results using Cohere's cross-encoder model. This pipeline forms the core of AskChuck's ability to find relevant chunks from Owen's literature using both semantic and lexical signals, with support for hierarchical parent-child expansion and figure-aware retrieval.

**The shift from v1.0:** Instead of manually combining two separate indices (Chroma dense + BM25 sparse) with custom RRF fusion, we now leverage Pinecone's native hybrid search that automatically fuses dense and sparse vectors in a single query. This dramatically simplifies the retrieval architecture while maintaining SOTA performance.

---

## Background

The retrieval pipeline must handle two fundamentally different query patterns. Some users will use Owen's exact terminology, asking about "Design Factors" or "VTCON clustering." Others will describe concepts in their own words, asking about "how to capture insights" or "organizing problem elements." Neither dense nor sparse retrieval alone handles both patterns well.

Dense retrieval using embeddings excels at semantic matching. A query about "categorizing items from specific to general" will match chunks about "Abstraction Ladders" because the embedding model understands the conceptual similarity. However, dense retrieval can miss exact terms—searching for "RELATN program" might retrieve general content about relationship analysis rather than the specific RELATN tool.

Sparse retrieval using BM25 excels at exact matching. It ensures that a query containing "Design Factor" retrieves chunks with those exact words. But BM25 fails on paraphrases—a query about "documenting insights" won't match chunks that use "Design Factor" to describe the same concept.

Hybrid retrieval combines both approaches. Research shows this combination improves retrieval quality by 15-30% over either method alone. **Pinecone Serverless provides native hybrid search**, eliminating the need for separate indices and manual fusion logic.

Cross-encoder reranking adds a second stage of refinement. While bi-encoders (like Voyage AI embeddings) encode queries and documents independently, cross-encoders process them together, enabling deeper semantic understanding at the cost of computational overhead. By retrieving broadly with hybrid search (top-50) and reranking precisely with a cross-encoder (top-5), we achieve high recall and high precision.

**Hierarchical retrieval** adds another dimension. Some queries need specific details (child chunks at 512 tokens), while others benefit from broader context (parent chunks at 2048 tokens). Our strategy: retrieve child chunks by default, optionally expand to include parent chunks, then rerank everything together to select the most relevant passages.

---

## Functional Requirements

### FR-01: Pinecone Hybrid Query

The system shall retrieve candidate chunks using Pinecone's native hybrid search combining dense and sparse vectors.

**Acceptance Criteria:**
- Embeds query using Voyage AI (from PRD-04)
- Generates sparse vector using saved BM25Encoder (from PRD-04)
- Queries Pinecone with both `vector` (dense) and `sparse_vector` (sparse)
- Uses configurable `alpha` parameter (0.0 = pure BM25, 1.0 = pure semantic)
- Supports metadata filtering (document_id, chunk_type, chunk_level)
- Returns top-k results with Pinecone's fused scores
- Default alpha: 0.5 (equal weight), tunable via evaluation

### FR-02: Hierarchical Parent-Child Expansion

The system shall optionally expand child chunk results to include parent chunks for broader context.

**Acceptance Criteria:**
- Identifies child chunks in results via `chunk_level="child"` metadata
- Fetches parent chunks using `parent_id` from metadata
- Adds parent chunks to candidate pool before reranking
- Expansion is configurable (enabled by default, can be disabled)
- Prevents duplicate chunks if parent already retrieved
- Preserves original retrieval scores for both parent and child

### FR-03: Cross-Encoder Reranking

The system shall rerank top candidates using Cohere's rerank API.

**Acceptance Criteria:**
- Sends query + top candidates to Cohere rerank-v3.0
- Returns reordered results with relevance scores
- Handles API rate limits gracefully (fallback to original order)
- Supports context-aware reranking (with conversation history)
- Truncates long documents to 4000 chars for API limits

### FR-04: Figure-Aware Retrieval

The system shall support retrieval specifically targeting figure chunks.

**Acceptance Criteria:**
- Filters for `chunk_type="figure"` when requested
- Includes figure metadata (r2_url, caption) in results
- Can combine with text retrieval for mixed results
- Leverages `explicit_figures` and `related_figures` metadata for figure-text relationships

### FR-05: Query Expansion

The system shall optionally expand queries with related Owen terminology.

**Acceptance Criteria:**
- Uses Owen glossary to identify terms in query
- Adds related terms to improve recall
- Expansion is configurable (off by default)
- Logs expanded queries for debugging

### FR-06: Neighbor Chunk Retrieval (Optional)

The system shall optionally fetch neighboring chunks for contextual expansion.

**Acceptance Criteria:**
- Uses `neighbor_chunk_ids` metadata to find adjacent chunks
- Fetches neighbors from Pinecone by ID
- Adds neighbors to context without affecting ranking
- Useful for reading coherent multi-chunk passages

---

## Technical Specification

### Retrieval Flow (v2.0 - Pinecone Native Hybrid)

```
┌─────────────┐
│   Query     │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│      Optional Query Expansion        │
│    (Owen Glossary - Groq LLM)        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│        Query Processing              │
│  ┌─────────────┐  ┌─────────────┐   │
│  │  Voyage AI  │  │ BM25Encoder │   │
│  │   Embed     │  │   Sparse    │   │
│  │  (1024-dim) │  │   Vector    │   │
│  └──────┬──────┘  └──────┬──────┘   │
└─────────┼────────────────┼──────────┘
          │                │
          └────────┬───────┘
                   │
                   ▼
       ┌───────────────────────┐
       │   Pinecone Hybrid     │
       │   Query (top-50)      │
       │ alpha=0.5 (default)   │
       │ - Dense + Sparse      │
       │ - Auto RRF Fusion     │
       └──────────┬────────────┘
                  │
                  ▼
       ┌───────────────────────┐
       │ Optional Parent-Child │
       │    Expansion          │
       │ (add parent chunks)   │
       └──────────┬────────────┘
                  │
                  ▼
       ┌───────────────────────┐
       │   Cohere Rerank       │
       │   rerank-v3.0         │
       │   (top-5)             │
       └──────────┬────────────┘
                  │
                  ▼
       ┌───────────────────────┐
       │   Results + Metadata  │
       │   (enriched for UI)   │
       └───────────────────────┘
```

### Pinecone Alpha Parameter

Pinecone's `alpha` parameter controls the dense/sparse weighting:

```
alpha = 0.0  →  100% sparse (pure BM25 keyword matching)
alpha = 0.5  →  50/50 balanced hybrid (default)
alpha = 1.0  →  100% dense (pure semantic similarity)
```

**Our strategy:**
- **Default:** `alpha=0.5` (equal weighting)
- **Tuning:** Adjust based on PRD-08 evaluation metrics
- **Use cases:**
  - Exact term queries (e.g., "VTCON") → may benefit from lower alpha (more BM25)
  - Conceptual queries (e.g., "how to organize ideas") → may benefit from higher alpha (more semantic)

### Hierarchical Expansion Logic

**When to expand child → parent:**

1. **Query indicates broad conceptual question:**
   - Examples: "Explain Structured Planning", "What is Owen's methodology"
   - Heuristic: Query length > 10 words, no Owen-specific terms

2. **Child chunk relevance is high:**
   - If child chunk scores > 0.8 relevance, likely worth expanding to parent
   - Parent provides document-level context child lacks

3. **Configurable expansion:**
   ```python
   expand_to_parents: bool = True  # Default: enabled
   expansion_threshold: float = 0.7  # Only expand high-scoring children
   ```

**Implementation:**
```python
# Pseudo-code for expansion
candidates = pinecone.query(query_vector, sparse_vector, top_k=50)

if expand_to_parents:
    parent_ids = set()
    for chunk in candidates:
        if chunk.metadata["chunk_level"] == "child":
            if chunk.score >= expansion_threshold:
                parent_id = chunk.metadata.get("parent_id")
                if parent_id and parent_id not in [c.id for c in candidates]:
                    parent_ids.add(parent_id)

    # Fetch parents by ID
    parents = pinecone.fetch(ids=list(parent_ids))
    candidates.extend(parents.vectors)

# Rerank combined pool
reranked = cohere.rerank(query, candidates, top_k=5)
```

---

## Implementation Details

### File: src/retrieval/query_expansion.py

```python
"""
Query expansion using Owen terminology glossary.
Adds related terms to improve recall for specialized vocabulary.
"""

import logging
from typing import Optional

from groq import Groq
from src.utils.config import settings
from src.utils.owen_glossary import OWEN_GLOSSARY

logger = logging.getLogger(__name__)


class QueryExpander:
    """
    Expands queries with related Owen methodology terms.

    Uses the Owen glossary to identify domain-specific terminology
    and adds related terms to improve retrieval recall.
    """

    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = "llama-3.3-70b-versatile"

    def expand_query(
        self,
        query: str,
        max_expansions: int = 3
    ) -> str:
        """
        Expand query with related Owen terms.

        Args:
            query: The original user query
            max_expansions: Maximum number of related terms to add

        Returns:
            Expanded query string
        """
        # Build prompt with glossary
        glossary_text = "\n".join([
            f"- {term}: {defn}"
            for term, defn in list(OWEN_GLOSSARY.items())[:20]  # Top 20 most common
        ])

        prompt = f"""You are an expert in Charles Owen's Structured Planning methodology.

Given this user query: "{query}"

And this glossary of Owen terminology:
{glossary_text}

Identify up to {max_expansions} related Owen terms that would improve retrieval, and return them as a comma-separated list.
Only include terms that are clearly relevant to the query.
If no relevant terms exist, return "NONE".

Related terms:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=50
            )

            expansion_text = response.choices[0].message.content.strip()

            if expansion_text == "NONE" or not expansion_text:
                logger.debug(f"No expansion terms found for: {query}")
                return query

            # Parse comma-separated terms
            terms = [t.strip() for t in expansion_text.split(",")]
            expanded = f"{query} {' '.join(terms)}"

            logger.info(f"Expanded query: '{query}' → '{expanded}'")
            return expanded

        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            return query


# Global instance
_expander: Optional[QueryExpander] = None


def get_query_expander() -> QueryExpander:
    """Get or create the global query expander instance."""
    global _expander
    if _expander is None:
        _expander = QueryExpander()
    return _expander


def expand_query(query: str, max_expansions: int = 3) -> str:
    """Convenience function to expand a query."""
    return get_query_expander().expand_query(query, max_expansions)
```

### File: src/retrieval/pinecone_retriever.py

```python
"""
Pinecone native hybrid search retriever.
Queries the Pinecone index with both dense (Voyage AI) and sparse (BM25) vectors.
"""

import logging
from typing import Optional, List, Dict

from pinecone import Pinecone
from src.indexing.embeddings import VoyageEmbedder
from src.indexing.sparse_encoder import OwenSparseEncoder
from src.utils.config import settings

logger = logging.getLogger(__name__)


class PineconeHybridRetriever:
    """
    Retrieves chunks using Pinecone's native hybrid search.

    Combines dense (Voyage AI) and sparse (BM25) vectors in a single query.
    Pinecone automatically handles RRF fusion internally.
    """

    def __init__(
        self,
        alpha: float = 0.5,
        expand_to_parents: bool = True,
        expansion_threshold: float = 0.7
    ):
        """
        Initialize the Pinecone hybrid retriever.

        Args:
            alpha: Dense/sparse weighting (0.0=pure BM25, 1.0=pure semantic)
            expand_to_parents: Whether to add parent chunks to child results
            expansion_threshold: Min score to trigger parent expansion
        """
        # Initialize Pinecone
        pc = Pinecone(api_key=settings.pinecone_api_key)
        self.index = pc.Index(settings.pinecone_index_name)

        # Initialize embedding and sparse encoding
        self.embedder = VoyageEmbedder()
        self.sparse_encoder = OwenSparseEncoder()
        self.sparse_encoder.load()  # Load saved encoder from PRD-04

        self.alpha = alpha
        self.expand_to_parents = expand_to_parents
        self.expansion_threshold = expansion_threshold

        logger.info(f"PineconeHybridRetriever initialized (alpha={alpha})")

    def retrieve(
        self,
        query: str,
        top_k: int = 50,
        filter: Optional[Dict] = None,
        include_metadata: bool = True
    ) -> List[Dict]:
        """
        Retrieve relevant chunks using hybrid search.

        Args:
            query: The search query
            top_k: Number of results to return
            filter: Metadata filter dict (e.g., {"chunk_type": "text"})
            include_metadata: Whether to include full metadata

        Returns:
            List of result dictionaries with scores and metadata
        """
        # Generate dense vector
        dense_vector = self.embedder.embed_query(query)

        # Generate sparse vector
        sparse_vector = self.sparse_encoder.encode_query(query)

        # Query Pinecone with hybrid search
        results = self.index.query(
            vector=dense_vector,
            sparse_vector=sparse_vector,
            top_k=top_k,
            filter=filter,
            include_metadata=include_metadata,
            alpha=self.alpha  # Pinecone's alpha parameter
        )

        # Convert to standard format
        candidates = []
        for match in results.matches:
            candidate = {
                "chunk_id": match.id,
                "score": match.score,
                "metadata": match.metadata if include_metadata else {}
            }

            # Extract text from metadata
            if include_metadata:
                candidate["content"] = match.metadata.get("text", "")

            candidates.append(candidate)

        logger.info(f"Retrieved {len(candidates)} candidates for query: '{query[:50]}...'")

        return candidates

    def retrieve_with_expansion(
        self,
        query: str,
        top_k: int = 50,
        filter: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Retrieve with optional parent-child expansion.

        Args:
            query: The search query
            top_k: Number of initial candidates
            filter: Metadata filter dict

        Returns:
            List of candidates including expanded parents
        """
        # Initial retrieval
        candidates = self.retrieve(query, top_k, filter)

        if not self.expand_to_parents:
            return candidates

        # Identify high-scoring child chunks
        parent_ids = set()
        for chunk in candidates:
            metadata = chunk.get("metadata", {})
            chunk_level = metadata.get("chunk_level")
            parent_id = metadata.get("parent_id")

            # Expand if child chunk with high relevance
            if (chunk_level == "child" and
                parent_id and
                chunk["score"] >= self.expansion_threshold):

                # Check if parent already in results
                if parent_id not in [c["chunk_id"] for c in candidates]:
                    parent_ids.add(parent_id)

        if not parent_ids:
            logger.debug("No parent expansion needed")
            return candidates

        # Fetch parent chunks by ID
        logger.info(f"Expanding to {len(parent_ids)} parent chunks")
        fetch_response = self.index.fetch(ids=list(parent_ids))

        # Add parents to candidate pool
        for parent_id, vector_data in fetch_response.vectors.items():
            parent_chunk = {
                "chunk_id": parent_id,
                "score": 0.0,  # Parent has no retrieval score initially
                "metadata": vector_data.metadata,
                "content": vector_data.metadata.get("text", ""),
                "expanded_parent": True  # Flag for debugging
            }
            candidates.append(parent_chunk)

        logger.info(f"Expanded candidates: {len(candidates)} total (added {len(parent_ids)} parents)")

        return candidates

    def retrieve_figures(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict]:
        """Convenience method to retrieve only figure chunks."""
        filter = {"chunk_type": "figure"}
        return self.retrieve(query, top_k, filter)

    def retrieve_from_document(
        self,
        query: str,
        document_id: str,
        top_k: int = 10
    ) -> List[Dict]:
        """Convenience method to retrieve within a specific document."""
        filter = {"document_id": document_id}
        return self.retrieve(query, top_k, filter)

    def fetch_neighbors(
        self,
        chunk_id: str
    ) -> List[Dict]:
        """
        Fetch neighboring chunks for contextual expansion.

        Args:
            chunk_id: The chunk ID to fetch neighbors for

        Returns:
            List of neighbor chunks
        """
        # Fetch the chunk
        response = self.index.fetch(ids=[chunk_id])

        if not response.vectors:
            logger.warning(f"Chunk not found: {chunk_id}")
            return []

        chunk_data = response.vectors[chunk_id]
        neighbor_ids = chunk_data.metadata.get("neighbor_chunk_ids", "")

        if not neighbor_ids:
            return []

        # Parse comma-separated neighbor IDs
        if isinstance(neighbor_ids, str):
            neighbor_id_list = [n.strip() for n in neighbor_ids.split(",") if n.strip()]
        else:
            neighbor_id_list = neighbor_ids

        if not neighbor_id_list:
            return []

        # Fetch neighbors
        neighbors_response = self.index.fetch(ids=neighbor_id_list)

        neighbors = []
        for neighbor_id, vector_data in neighbors_response.vectors.items():
            neighbor = {
                "chunk_id": neighbor_id,
                "metadata": vector_data.metadata,
                "content": vector_data.metadata.get("text", "")
            }
            neighbors.append(neighbor)

        logger.debug(f"Fetched {len(neighbors)} neighbors for {chunk_id}")
        return neighbors


# Global instance
_retriever: Optional[PineconeHybridRetriever] = None


def get_retriever() -> PineconeHybridRetriever:
    """Get or create the global retriever instance."""
    global _retriever
    if _retriever is None:
        _retriever = PineconeHybridRetriever()
    return _retriever
```

### File: src/retrieval/reranker.py

```python
"""
Cross-encoder reranking using Cohere's rerank API.
Provides more accurate relevance scoring for top candidates.
"""

import logging
from typing import Optional, List, Dict

import cohere

from src.utils.config import settings

logger = logging.getLogger(__name__)


class CohereReranker:
    """
    Reranks retrieval results using Cohere's cross-encoder model.

    Cross-encoders process query and document together, enabling
    deeper semantic understanding than bi-encoder embeddings.
    We use this as a second stage after Pinecone hybrid retrieval
    to improve precision on the top results.
    """

    def __init__(self, model: str = "rerank-v3.0"):
        """
        Initialize the Cohere reranker.

        Args:
            model: Cohere rerank model name
        """
        self.client = cohere.ClientV2(api_key=settings.cohere_api_key)
        self.model = model

        logger.info(f"CohereReranker initialized with model: {self.model}")

    def rerank(
        self,
        query: str,
        results: List[Dict],
        top_k: int = 5
    ) -> List[Dict]:
        """
        Rerank retrieval results using cross-encoder scoring.

        Args:
            query: The search query
            results: List of retrieval results with 'content' field
            top_k: Number of results to return after reranking

        Returns:
            Reranked results with relevance scores
        """
        if not results:
            return []

        # Extract documents for reranking
        documents = []
        for r in results:
            content = r.get("content", "")
            # Truncate very long documents (Cohere has limits)
            if len(content) > 4000:
                content = content[:4000] + "..."
            documents.append(content)

        try:
            response = self.client.rerank(
                model=self.model,
                query=query,
                documents=documents,
                top_n=min(top_k, len(documents)),
                return_documents=False  # We already have the documents
            )

            # Build reranked results
            reranked = []
            for i, r in enumerate(response.results):
                original_result = results[r.index].copy()
                original_result["rerank_score"] = r.relevance_score
                original_result["rerank_rank"] = i + 1
                original_result["original_rank"] = r.index + 1
                reranked.append(original_result)

            logger.info(f"Reranked {len(results)} results to top {len(reranked)}")

            return reranked

        except Exception as e:
            logger.error(f"Cohere rerank failed: {e}. Returning original order.")
            return results[:top_k]

    def rerank_with_context(
        self,
        query: str,
        results: List[Dict],
        context: str = "",
        top_k: int = 5
    ) -> List[Dict]:
        """
        Rerank with additional context (e.g., conversation history).

        The context is prepended to the query to provide additional
        signals for relevance scoring.
        """
        if context:
            enhanced_query = f"{context}\n\nCurrent question: {query}"
        else:
            enhanced_query = query

        return self.rerank(enhanced_query, results, top_k)


# Global instance
_reranker: Optional[CohereReranker] = None


def get_reranker() -> CohereReranker:
    """Get or create the global reranker instance."""
    global _reranker
    if _reranker is None:
        _reranker = CohereReranker()
    return _reranker


def rerank_results(query: str, results: List[Dict], top_k: int = 5) -> List[Dict]:
    """Convenience function to rerank results."""
    return get_reranker().rerank(query, results, top_k)
```

### File: src/retrieval/retrieval_pipeline.py

```python
"""
Complete retrieval pipeline combining Pinecone hybrid search and Cohere reranking.
This is the main entry point for retrieval operations.
"""

import logging
from typing import Optional, List, Dict

from src.retrieval.pinecone_retriever import PineconeHybridRetriever, get_retriever
from src.retrieval.reranker import CohereReranker, get_reranker
from src.retrieval.query_expansion import QueryExpander, get_query_expander

logger = logging.getLogger(__name__)


class RetrievalPipeline:
    """
    Complete retrieval pipeline for AskChuck.

    Combines:
    1. Optional query expansion (Owen terminology)
    2. Pinecone hybrid search (dense + sparse with auto-fusion)
    3. Optional parent-child expansion
    4. Cohere cross-encoder reranking

    This multi-stage approach retrieves broadly first (high recall)
    then refines with precise scoring (high precision).
    """

    def __init__(
        self,
        retriever: PineconeHybridRetriever = None,
        reranker: CohereReranker = None,
        query_expander: QueryExpander = None,
        initial_k: int = 50,
        final_k: int = 5
    ):
        """
        Initialize the retrieval pipeline.

        Args:
            retriever: Pinecone hybrid retriever instance
            reranker: Cohere reranker instance
            query_expander: Query expander instance
            initial_k: Number of candidates from Pinecone
            final_k: Number of results after reranking
        """
        self.retriever = retriever or get_retriever()
        self.reranker = reranker or get_reranker()
        self.query_expander = query_expander or get_query_expander()
        self.initial_k = initial_k
        self.final_k = final_k

    def retrieve(
        self,
        query: str,
        top_k: int = None,
        expand_query: bool = False,
        expand_parents: bool = True,
        include_figures: bool = True,
        document_id: str = None,
        skip_rerank: bool = False
    ) -> List[Dict]:
        """
        Run the complete retrieval pipeline.

        Args:
            query: The search query
            top_k: Number of final results (default: self.final_k)
            expand_query: Whether to expand with Owen terminology
            expand_parents: Whether to add parent chunks to children
            include_figures: Whether to include figure chunks
            document_id: Filter to specific document
            skip_rerank: If True, skip reranking step

        Returns:
            List of relevant chunks with metadata and scores
        """
        top_k = top_k or self.final_k

        # Stage 0: Optional query expansion
        search_query = query
        if expand_query:
            search_query = self.query_expander.expand_query(query)

        # Stage 1: Pinecone hybrid retrieval
        filter_dict = {}
        if document_id:
            filter_dict["document_id"] = document_id

        if expand_parents:
            candidates = self.retriever.retrieve_with_expansion(
                search_query,
                top_k=self.initial_k,
                filter=filter_dict if filter_dict else None
            )
        else:
            candidates = self.retriever.retrieve(
                search_query,
                top_k=self.initial_k,
                filter=filter_dict if filter_dict else None
            )

        if not candidates:
            logger.warning(f"No candidates found for query: {query}")
            return []

        # Filter figures if requested
        if not include_figures:
            candidates = [
                c for c in candidates
                if c.get("metadata", {}).get("chunk_type") != "figure"
            ]

        # Stage 2: Reranking
        if skip_rerank or len(candidates) <= top_k:
            results = candidates[:top_k]
        else:
            results = self.reranker.rerank(query, candidates, top_k)

        # Enrich results with display-friendly format
        enriched_results = self._enrich_results(results)

        return enriched_results

    def retrieve_with_figures(
        self,
        query: str,
        text_k: int = 3,
        figure_k: int = 2,
        expand_query: bool = False
    ) -> Dict:
        """
        Retrieve both text and figure chunks separately.

        Useful for ensuring relevant figures are included
        even if they don't rank highest overall.

        Args:
            query: The search query
            text_k: Number of text chunks
            figure_k: Number of figure chunks
            expand_query: Whether to expand query

        Returns:
            Dict with 'text_chunks' and 'figure_chunks' lists
        """
        # Get text chunks (excluding figures)
        text_results = self.retrieve(
            query,
            top_k=text_k,
            expand_query=expand_query,
            include_figures=False
        )

        # Get figure chunks separately
        figure_results = self.retriever.retrieve_figures(query, top_k=figure_k)
        figure_results = self._enrich_results(figure_results)

        return {
            "text_chunks": text_results,
            "figure_chunks": figure_results
        }

    def retrieve_with_neighbors(
        self,
        query: str,
        top_k: int = None,
        include_neighbors: bool = True
    ) -> Dict:
        """
        Retrieve chunks and optionally include neighboring chunks.

        Useful for reading coherent multi-chunk passages.

        Args:
            query: The search query
            top_k: Number of main results
            include_neighbors: Whether to fetch neighbors

        Returns:
            Dict with 'main_chunks' and 'neighbor_chunks'
        """
        # Get main results
        main_results = self.retrieve(query, top_k=top_k)

        if not include_neighbors:
            return {
                "main_chunks": main_results,
                "neighbor_chunks": []
            }

        # Fetch neighbors for top result
        neighbors = []
        if main_results:
            top_chunk_id = main_results[0]["chunk_id"]
            neighbors = self.retriever.fetch_neighbors(top_chunk_id)
            neighbors = self._enrich_results(neighbors)

        return {
            "main_chunks": main_results,
            "neighbor_chunks": neighbors
        }

    def _enrich_results(self, results: List[Dict]) -> List[Dict]:
        """Add display-friendly fields to results."""
        enriched = []

        for r in results:
            result = r.copy()
            metadata = result.get("metadata", {})

            # Add convenience fields
            result["document_title"] = metadata.get("document_title", "Unknown")
            result["section"] = metadata.get("section", "")
            result["chunk_type"] = metadata.get("chunk_type", "text")
            result["chunk_level"] = metadata.get("chunk_level", "child")

            # Handle figures specially
            if result["chunk_type"] == "figure":
                result["figure_url"] = metadata.get("r2_url")  # Cloudflare R2
                result["figure_caption"] = metadata.get("caption", "")
                result["figure_number"] = metadata.get("figure_number")

            # Owen terms for display
            owen_terms_str = metadata.get("owen_terms", "")
            if isinstance(owen_terms_str, str):
                result["owen_terms"] = owen_terms_str.split(",") if owen_terms_str else []
            else:
                result["owen_terms"] = owen_terms_str or []

            # Parent/child info
            result["parent_id"] = metadata.get("parent_id")

            enriched.append(result)

        return enriched


# Global instance
_pipeline: Optional[RetrievalPipeline] = None


def get_retrieval_pipeline() -> RetrievalPipeline:
    """Get or create the global retrieval pipeline instance."""
    global _pipeline
    if _pipeline is None:
        _pipeline = RetrievalPipeline()
    return _pipeline


def retrieve(
    query: str,
    top_k: int = 5,
    expand_query: bool = False
) -> List[Dict]:
    """Convenience function to run retrieval."""
    return get_retrieval_pipeline().retrieve(
        query,
        top_k=top_k,
        expand_query=expand_query
    )
```

---

## Acceptance Criteria

| Criterion | Verification Method |
|-----------|-------------------|
| Pinecone hybrid query returns results | Test query returns both dense and sparse matches |
| Alpha parameter controls weighting | Compare results with alpha=0.0, 0.5, 1.0 |
| Parent-child expansion works | Verify child chunks get parent context added |
| Cohere reranking improves order | Compare relevance before/after rerank |
| Figure filtering works | Query with filter `chunk_type="figure"` |
| Document filtering works | Query with specific document_id |
| Query expansion adds Owen terms | Check expanded query includes glossary terms |
| Neighbor chunk retrieval works | Fetch neighbors for chunk, verify sequential IDs |
| Rate limits handled gracefully | Trigger Cohere limit, verify fallback |
| Full pipeline returns enriched results | Check for r2_url, chunk_level, parent_id fields |

---

## Testing Queries

Use these queries to verify retrieval quality:

**Exact terminology (should favor sparse/BM25):**
- "What is VTCON?"
- "Design Factor Observation Extension"
- "Means/Ends Analysis"

**Semantic paraphrasing (should favor dense/embedding):**
- "How to categorize things from specific to general"
- "Documenting insights about problems"
- "Organizing functions by shared solutions"

**Mixed queries (hybrid should excel):**
- "What is the Abstraction Ladder and how does it work?"
- "Examples of Design Factors in housing projects"

**Figure queries:**
- "Show me a diagram of an Information Structure"
- "Housing system Abstraction Structure figure"

**Broad conceptual queries (should trigger parent expansion):**
- "Explain Structured Planning methodology"
- "What are Owen's core principles for design research"

---

## Configuration Parameters

| Parameter | Default | Purpose | Tuning Guidance |
|-----------|---------|---------|-----------------|
| `alpha` | 0.5 | Dense/sparse weight | Lower for exact terms, higher for concepts |
| `initial_k` | 50 | Candidates from Pinecone | Higher for complex queries, lower for speed |
| `final_k` | 5 | Results after rerank | Based on context window for generation |
| `expand_to_parents` | True | Add parent chunks | Disable for speed, enable for context |
| `expansion_threshold` | 0.7 | Min score for expansion | Higher = fewer parents added |
| `expand_query` | False | Add Owen terms | Enable for user queries, disable for Owen-fluent queries |

---

## Next Steps

Once retrieval is working, proceed to **PRD-06: Generation** to build the RAG chain that synthesizes responses from retrieved chunks.
