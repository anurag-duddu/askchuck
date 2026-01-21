"""
Retrieval pipeline for AskChuck RAG system.

This package provides the retrieval components for finding relevant
chunks from Owen's literature using hybrid search and reranking.

Main components:
- query_expansion: Expand queries with Owen terminology
- pinecone_retriever: Pinecone hybrid search (dense + sparse)
- reranker: Cohere cross-encoder reranking
- retrieval_pipeline: Complete orchestrated pipeline
"""

__all__ = [
    "QueryExpander",
    "expand_query",
    "PineconeHybridRetriever",
    "get_retriever",
    "CohereReranker",
    "rerank_results",
    "RetrievalPipeline",
    "retrieve",
]
