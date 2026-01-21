"""
Complete RAG chain for AskChuck.
Orchestrates retrieval, prompt construction, and generation.
"""

import logging
from typing import Dict, Generator, List, Optional

from groq import Groq

from src.generation.prompts import build_full_prompt
from src.retrieval.retrieval_pipeline import RetrievalPipeline, get_retrieval_pipeline
from src.utils.config import settings

logger = logging.getLogger(__name__)


class AskChuckRAG:
    """
    Main RAG chain for AskChuck.

    Orchestrates the complete flow from question to answer:
    1. Retrieve relevant chunks using Pinecone hybrid search + reranking (PRD-05)
    2. Construct optimized prompt with context and history
    3. Generate response using Groq Llama 3.3 70B
    4. Extract figures (Cloudflare R2 URLs) and format final response with chunk IDs
    """

    def __init__(
        self,
        retrieval_pipeline: Optional[RetrievalPipeline] = None,
        model: str = "llama-3.3-70b-versatile",  # Llama 3.3 70B (128K context)
        temperature: float = 0.2,
        max_tokens: int = 1500,
    ):
        """
        Initialize the RAG chain.

        Args:
            retrieval_pipeline: Pipeline for retrieving relevant chunks (PRD-05)
            model: Groq model name (default: Llama 3.3 70B)
            temperature: Generation temperature (lower = more focused)
            max_tokens: Maximum tokens in response
        """
        self.retrieval = retrieval_pipeline or get_retrieval_pipeline()
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        logger.info(f"AskChuckRAG initialized with model: {self.model}")

    def query(
        self,
        question: str,
        conversation_history: Optional[List[dict]] = None,
        include_figures: bool = True,
        top_k: int = 5,
    ) -> Dict:
        """
        Process a question and generate a response.

        Args:
            question: The user's question
            conversation_history: Previous messages for context
            include_figures: Whether to retrieve and include figures
            top_k: Number of text chunks to retrieve

        Returns:
            Dictionary with:
            - answer: The generated response text
            - sources: List of source chunks with [Document, Section] format
            - chunk_ids: List of chunk IDs used (for debugging/tracing)
            - figures: List of relevant figures with Cloudflare R2 URLs
        """
        logger.info(f"Processing query: {question[:100]}...")

        # Step 1: Retrieve relevant chunks via PRD-05 pipeline
        # Includes Pinecone hybrid search, parent-child expansion, Cohere reranking
        all_chunks = self.retrieval.retrieve(
            query=question,
            top_k=top_k,
            include_figures=include_figures,
            expand_parents=True,  # Use hierarchical expansion from PRD-05
        )

        if not all_chunks:
            logger.warning("No relevant chunks found")
            return self._no_context_response(question)

        # Step 2: Build prompt (handles parent/child chunks + figures)
        system_prompt, user_prompt = build_full_prompt(
            question=question,
            context_chunks=all_chunks,
            conversation_history=conversation_history,
        )

        # Step 3: Generate response using Llama 3.3 70B
        answer = self._generate(system_prompt, user_prompt)

        # Step 4: Extract figures for display (Cloudflare R2 URLs)
        figures = self._extract_display_figures(all_chunks)

        # Step 5: Build sources list (hybrid format: display + chunk_ids)
        sources = self._build_sources_list(all_chunks)
        chunk_ids = [chunk.get("chunk_id") for chunk in all_chunks]

        return {
            "answer": answer,
            "sources": sources,  # [Document, Section] format for display
            "chunk_ids": chunk_ids,  # Chunk IDs for debugging/tracing
            "figures": figures,  # Cloudflare R2 URLs
            "chunks_used": len(all_chunks),
        }

    def _generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate response using Groq Llama 3.3 70B."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return f"I encountered an error generating a response. Please try again. (Error: {str(e)[:100]})"

    def stream_query(
        self,
        question: str,
        conversation_history: Optional[List[dict]] = None,
        include_figures: bool = True,
        top_k: int = 5,
    ) -> Generator[Dict, None, None]:
        """
        Stream a response token by token.

        Yields dictionaries with either:
        - {"type": "token", "content": "..."} for text tokens
        - {"type": "figures", "figures": [...]} at the end
        - {"type": "sources", "sources": [...]} at the end
        - {"type": "chunk_ids", "chunk_ids": [...]} at the end
        - {"type": "done"} when complete
        """
        logger.info(f"Streaming query: {question[:100]}...")

        # Retrieve (not streamed)
        all_chunks = self.retrieval.retrieve(
            query=question,
            top_k=top_k,
            include_figures=include_figures,
            expand_parents=True,
        )

        if not all_chunks:
            yield {
                "type": "token",
                "content": "I couldn't find relevant information in Owen's literature for this question.",
            }
            yield {"type": "done"}
            return

        # Build prompt
        system_prompt, user_prompt = build_full_prompt(
            question=question,
            context_chunks=all_chunks,
            conversation_history=conversation_history,
        )

        # Stream generation
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield {"type": "token", "content": chunk.choices[0].delta.content}

        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            yield {"type": "token", "content": f"\n\n[Error: {str(e)[:100]}]"}

        # Yield metadata at the end
        figures = self._extract_display_figures(all_chunks)
        if figures:
            yield {"type": "figures", "figures": figures}

        sources = self._build_sources_list(all_chunks)
        yield {"type": "sources", "sources": sources}

        chunk_ids = [chunk.get("chunk_id") for chunk in all_chunks]
        yield {"type": "chunk_ids", "chunk_ids": chunk_ids}

        yield {"type": "done"}

    def _no_context_response(self, question: str) -> Dict:
        """Generate response when no context is found."""
        return {
            "answer": (
                "I couldn't find specific information about this in Owen's literature. "
                "This might be because:\n\n"
                "1. The topic isn't covered in the available documents\n"
                "2. The question uses different terminology than Owen's methodology\n"
                "3. This is a very specific question that requires broader context\n\n"
                "Could you try rephrasing your question, or ask about a related topic "
                "like Functions, Design Factors, Information Structures, or Abstraction Ladders?"
            ),
            "sources": [],
            "chunk_ids": [],
            "figures": [],
            "chunks_used": 0,
        }

    def _extract_display_figures(self, all_chunks: List[dict]) -> List[dict]:
        """
        Extract figures for display in the response (Cloudflare R2 URLs).
        Maximum 3 figures to prevent UI clutter.
        """
        figures = []
        seen_urls = set()

        for chunk in all_chunks:
            if chunk.get("chunk_type") == "figure":
                metadata = chunk.get("metadata", {})
                url = metadata.get("figure_url", "")  # Cloudflare R2 URL

                if url and url not in seen_urls:
                    figures.append(
                        {
                            "url": url,
                            "caption": metadata.get("caption", ""),
                            "document": chunk.get("document_title", ""),
                            "figure_number": metadata.get("figure_number", 0),
                            "description": chunk.get("content", ""),
                        }
                    )
                    seen_urls.add(url)

                    # Limit to 3 figures
                    if len(figures) >= 3:
                        break

        return figures

    def _build_sources_list(self, chunks: List[dict]) -> List[dict]:
        """
        Build deduplicated list of sources in [Document, Section] format.
        Includes chunk metadata for debugging.
        """
        sources = []
        seen = set()

        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            doc_title = chunk.get("document_title", "Unknown")
            section = chunk.get("section", "")
            key = (doc_title, section)

            if key not in seen:
                sources.append(
                    {
                        "display": f"[{doc_title}, {section}]" if section else f"[{doc_title}]",  # User-facing format
                        "document": doc_title,
                        "section": section,
                        "chunk_id": chunk.get("chunk_id"),
                        "chunk_level": chunk.get("chunk_level", "unknown"),
                    }
                )
                seen.add(key)

        return sources


# Global instance
_rag_chain: Optional[AskChuckRAG] = None


def get_rag_chain() -> AskChuckRAG:
    """Get or create the global RAG chain instance."""
    global _rag_chain
    if _rag_chain is None:
        _rag_chain = AskChuckRAG()
    return _rag_chain


def ask(question: str, history: Optional[List[dict]] = None) -> Dict:
    """Convenience function to query AskChuck."""
    return get_rag_chain().query(question, conversation_history=history)
