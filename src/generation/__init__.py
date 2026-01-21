"""
Generation layer for AskChuck RAG system.

This package provides the components for generating responses from retrieved
chunks using Groq's Llama 3.3 70B model.

Main components:
- prompts: Prompt templates and formatting
- rag_chain: Complete RAG orchestration
"""

__all__ = [
    "build_full_prompt",
    "format_context_chunks",
    "AskChuckRAG",
    "ask",
    "get_rag_chain",
]
