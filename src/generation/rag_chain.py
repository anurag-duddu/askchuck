"""
Complete RAG chain for AskChuck.
Orchestrates retrieval, prompt construction, and generation.
"""

import logging
import os
import re
import threading
from difflib import SequenceMatcher
from typing import Dict, Generator, List, Optional

from groq import Groq

from src.generation.prompts import build_full_prompt, group_chunks_by_source
from src.retrieval.retrieval_pipeline import (RetrievalPipeline,
                                              get_retrieval_pipeline)
from src.utils.config import RAW_DIR, settings

logger = logging.getLogger(__name__)

# LangSmith tracing setup
try:
    from langsmith import traceable
    from langsmith.run_helpers import get_current_run_tree

    LANGSMITH_ENABLED = bool(settings.langchain_api_key)
    if LANGSMITH_ENABLED:
        # Ensure environment variables are set for LangSmith
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
        logger.info("LangSmith tracing enabled for AskChuckRAG")
except ImportError:
    LANGSMITH_ENABLED = False

    # Create no-op decorator if langsmith not installed
    def traceable(*args, **kwargs):
        def decorator(func):
            return func

        return decorator if not args else args[0]

    logger.info("LangSmith not installed - tracing disabled")

# Thread-safe singleton lock
_rag_chain_lock = threading.Lock()
_rag_chain: Optional["AskChuckRAG"] = None


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

        # Cache PDF files at initialization for performance
        self._pdf_file_cache: Optional[List[str]] = None
        self._refresh_pdf_cache()

        logger.info(f"AskChuckRAG initialized with model: {self.model}")

    def _refresh_pdf_cache(self) -> None:
        """Refresh the cached list of PDF files."""
        try:
            if RAW_DIR.exists():
                self._pdf_file_cache = [p.name for p in RAW_DIR.glob("*.pdf")]
                logger.debug(f"PDF cache refreshed: {len(self._pdf_file_cache)} files")
            else:
                self._pdf_file_cache = []
                logger.warning(f"RAW_DIR does not exist: {RAW_DIR}")
        except OSError as e:
            logger.error(f"Failed to refresh PDF cache: {e}")
            self._pdf_file_cache = []

    def _get_pdf_files(self) -> List[str]:
        """Get cached PDF file list, refreshing if needed."""
        if self._pdf_file_cache is None:
            self._refresh_pdf_cache()
        return self._pdf_file_cache or []

    @traceable(name="askchuck_query", run_type="chain")
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
        # Use retrieve_with_figures to get both text and figures separately
        if include_figures:
            retrieval_results = self.retrieval.retrieve_with_figures(
                query=question,
                text_k=top_k,
                figure_k=3,  # Get up to 3 relevant figures
            )
            all_chunks = retrieval_results.get("text_chunks", [])
            figure_chunks = retrieval_results.get("figure_chunks", [])
            # Combine for context (figures added at end)
            all_chunks = all_chunks + figure_chunks
        else:
            all_chunks = self.retrieval.retrieve(
                query=question,
                top_k=top_k,
                include_figures=False,
                expand_parents=True,
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

    # Fallback models in order of preference (for rate limit handling)
    # Note: Avoid Qwen for streaming as it outputs <think> tags
    FALLBACK_MODELS = [
        "llama-3.3-70b-versatile",  # Primary: best quality
        "meta-llama/llama-4-scout-17b-16e-instruct",  # Fallback 1: newer Llama
        "llama-3.1-8b-instant",  # Fallback 2: fast, high limits
        "qwen/qwen3-32b",  # Fallback 3: good but has thinking tags
    ]

    def _clean_model_output(self, content: str) -> str:
        """Clean up model output - remove thinking tags, artifacts, etc."""
        if not content:
            return content

        # Remove <think>...</think> tags (used by Qwen and some other models)
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)

        # Remove other common artifacts
        content = re.sub(r"<\|.*?\|>", "", content)  # Special tokens

        return content.strip()

    @traceable(name="llm_generate", run_type="llm")
    def _generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate response with automatic model fallback on rate limits."""
        # Build list of models to try (current model first, then fallbacks)
        models_to_try = [self.model]
        for fallback in self.FALLBACK_MODELS:
            if fallback not in models_to_try:
                models_to_try.append(fallback)

        last_error = None
        for model in models_to_try:
            try:
                logger.debug(f"Attempting generation with model: {model}")
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )

                if model != self.model:
                    logger.info(f"Successfully used fallback model: {model}")

                content = response.choices[0].message.content
                # Clean up thinking tags from some models (e.g., Qwen)
                content = self._clean_model_output(content)
                return content

            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                # Check if it's a rate limit error
                if "429" in str(e) or "rate limit" in error_str:
                    logger.warning(f"Rate limited on {model}, trying next fallback...")
                    continue
                else:
                    # Non-rate-limit error, don't try fallbacks
                    logger.error(f"Generation failed with {model}: {e}")
                    break

        logger.error(f"All models failed. Last error: {last_error}")
        return f"I encountered an error generating a response. Please try again. (Error: {str(last_error)[:100]})"

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

        # Stream generation with fallback
        models_to_try = [self.model]
        for fallback in self.FALLBACK_MODELS:
            if fallback not in models_to_try:
                models_to_try.append(fallback)

        stream_success = False
        for model in models_to_try:
            try:
                logger.debug(f"Attempting streaming with model: {model}")
                stream = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    stream=True,
                )

                if model != self.model:
                    logger.info(f"Using fallback model for streaming: {model}")

                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield {
                            "type": "token",
                            "content": chunk.choices[0].delta.content,
                        }

                stream_success = True
                break  # Success, exit the model loop

            except Exception as e:
                error_str = str(e).lower()
                if "429" in str(e) or "rate limit" in error_str:
                    logger.warning(f"Rate limited on {model}, trying next fallback...")
                    continue
                else:
                    logger.error(f"Streaming failed with {model}: {e}")
                    yield {"type": "token", "content": f"\n\n[Error: {str(e)[:100]}]"}
                    stream_success = (
                        True  # Don't try more models for non-rate-limit errors
                    )
                    break

        if not stream_success:
            yield {
                "type": "token",
                "content": "\n\n[Error: All models rate limited. Please try again later.]",
            }

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
        Extract figures for display in the response.
        Maximum 3 figures to prevent UI clutter.
        """
        figures = []
        seen_ids = set()

        for chunk in all_chunks:
            try:
                if chunk.get("chunk_type") == "figure":
                    metadata = chunk.get("metadata") or {}
                    chunk_id = chunk.get("chunk_id", "")

                    if chunk_id and chunk_id not in seen_ids:
                        # Build Supabase URL from chunk_id
                        url = self._get_figure_url(chunk_id)

                        figures.append(
                            {
                                "url": url,
                                "caption": metadata.get("caption", ""),
                                "document": chunk.get("document_title", ""),
                                "figure_number": metadata.get("figure_number", 0),
                                "description": chunk.get("content", ""),
                            }
                        )
                        seen_ids.add(chunk_id)

                        # Limit to 3 figures
                        if len(figures) >= 3:
                            break
            except Exception as e:
                logger.warning(f"Error extracting figure from chunk: {e}")
                continue

        return figures

    def _get_figure_url(self, figure_id: str) -> str:
        """Build Supabase Storage URL for a figure."""
        bucket = settings.supabase_storage_bucket
        return f"{settings.supabase_url}/storage/v1/object/public/{bucket}/figures/{figure_id}.png"

    def _infer_pdf_filename(self, document_id: str, chunk_id: str) -> Optional[str]:
        """
        Infer PDF filename from document_id using fuzzy matching.
        Uses cached PDF file list for performance.

        Args:
            document_id: The document ID from chunk metadata
            chunk_id: The chunk ID (used for logging)

        Returns:
            Best matching PDF filename, or None if no good match found
        """
        if not document_id:
            return None

        pdf_names = self._get_pdf_files()
        if not pdf_names:
            logger.debug("No PDF files in cache")
            return None

        try:
            # Normalize document_id for matching
            doc_normalized = document_id.lower().replace("_", "").replace("-", "")

            best_match = None
            best_ratio = 0.5  # Minimum threshold for a match

            for pdf_name in pdf_names:
                # Normalize PDF name for matching
                pdf_normalized = (
                    pdf_name.lower()
                    .replace("-", "")
                    .replace("_", "")
                    .replace(".pdf", "")
                )

                # Use SequenceMatcher for fuzzy matching
                ratio = SequenceMatcher(None, doc_normalized, pdf_normalized).ratio()

                if ratio > best_ratio:
                    best_match = pdf_name
                    best_ratio = ratio

            if best_match:
                logger.debug(
                    f"Inferred PDF: {document_id} -> {best_match} (confidence: {best_ratio:.2f})"
                )
                return best_match
            else:
                logger.debug(f"No PDF match found for document_id: {document_id}")
                return None

        except Exception as e:
            logger.error(f"PDF inference failed for {document_id}: {e}")
            return None

    def _build_sources_list(self, chunks: List[dict]) -> List[dict]:
        """
        Build deduplicated list of sources in [Document, Section] format.
        Includes page number and PDF URL for navigation.

        IMPORTANT: Uses the same grouping logic as format_context_chunks()
        to ensure source numbers [1], [2], [3] match the LLM's citations.
        """
        try:
            from src.ingestion.pdf_uploader import get_pdf_uploader

            pdf_uploader = get_pdf_uploader()
        except Exception as e:
            logger.error(f"Failed to get PDF uploader: {e}")
            pdf_uploader = None

        sources = []

        # Filter to text chunks only (same as format_context_chunks)
        text_chunks = [
            c for c in chunks if isinstance(c, dict) and c.get("chunk_type") != "figure"
        ]

        # Use the same grouping function as prompts.py for consistency
        grouped_sources = group_chunks_by_source(text_chunks)

        for source_num, (doc_title, section), chunk_list in grouped_sources:
            try:
                # Use the first chunk for metadata (they share the same source)
                first_chunk = chunk_list[0]
                metadata = first_chunk.get("metadata")
                if not isinstance(metadata, dict):
                    metadata = {}

                # Find the best page_start among all chunks in group (prefer earliest)
                page_start = None
                for chunk in chunk_list:
                    chunk_meta = chunk.get("metadata", {})
                    p = chunk_meta.get("page_start") or chunk.get("page_start")
                    if p is not None:
                        try:
                            p = int(p)
                            if page_start is None or p < page_start:
                                page_start = p
                        except (ValueError, TypeError):
                            pass
                if page_start is None:
                    page_start = 1

                # Get PDF filename from first chunk
                pdf_filename = (
                    metadata.get("pdf_filename")
                    or first_chunk.get("pdf_filename")
                    or ""
                )

                # Fallback: try to infer PDF filename from document_id
                if not pdf_filename:
                    document_id = (
                        first_chunk.get("document_id")
                        or metadata.get("document_id")
                        or ""
                    )
                    chunk_id = first_chunk.get("chunk_id", "")
                    try:
                        pdf_filename = (
                            self._infer_pdf_filename(document_id, chunk_id) or ""
                        )
                    except Exception as e:
                        logger.warning(
                            f"PDF inference failed for chunk {chunk_id}: {e}"
                        )
                        pdf_filename = ""

                # Build PDF URL with page anchor
                pdf_url = ""
                if pdf_filename and pdf_uploader:
                    try:
                        base_url = pdf_uploader.get_pdf_url(pdf_filename)
                        if base_url:
                            pdf_url = f"{base_url}#page={page_start}"
                    except Exception as e:
                        logger.warning(f"Failed to get PDF URL for {pdf_filename}: {e}")

                # Clean up display string
                section_clean = section.strip() if section else ""
                if section_clean:
                    display = f"[{doc_title}, {section_clean}]"
                else:
                    display = f"[{doc_title}]"

                # Extract highlight text from first chunk (best representative)
                content = first_chunk.get("content", "") or ""
                # Remove page markers and metadata artifacts
                clean_content = re.sub(r"===\s*Page\s*\d+\s*===", "", content)
                clean_content = re.sub(
                    r"^\s*Institute of Design.*?TECHNOLOGY\s*",
                    "",
                    clean_content,
                    flags=re.IGNORECASE,
                )
                clean_content = clean_content.strip()
                # Pass substantial chunk content for contiguous block highlighting
                # Frontend will find this text block on the page and highlight it
                # Limit to 500 chars to keep URL reasonable but enough for unique match
                highlight_text = clean_content[:500].strip() if clean_content else ""

                # Collect chunk levels from all chunks in group
                chunk_levels = set()
                for chunk in chunk_list:
                    level = (
                        chunk.get("chunk_level")
                        or chunk.get("metadata", {}).get("level")
                        or "unknown"
                    )
                    chunk_levels.add(level)

                sources.append(
                    {
                        "display": display,
                        "document": doc_title,
                        "section": section_clean,
                        "chunk_id": first_chunk.get("chunk_id", ""),
                        "chunk_level": ", ".join(sorted(chunk_levels)),
                        # Navigation fields
                        "page_start": page_start,
                        "pdf_url": pdf_url,
                        "highlight_text": highlight_text if highlight_text else None,
                        # Source number for debugging (matches LLM citation)
                        "source_number": source_num,
                    }
                )

            except Exception as e:
                logger.error(f"Error processing source group: {e}")
                continue

        return sources


def get_rag_chain() -> AskChuckRAG:
    """
    Get or create the global RAG chain instance (thread-safe).

    Uses double-checked locking pattern for thread safety.
    """
    global _rag_chain
    if _rag_chain is None:
        with _rag_chain_lock:
            if _rag_chain is None:
                _rag_chain = AskChuckRAG()
    return _rag_chain


def ask(question: str, history: Optional[List[dict]] = None) -> Dict:
    """Convenience function to query AskChuck."""
    return get_rag_chain().query(question, conversation_history=history)
