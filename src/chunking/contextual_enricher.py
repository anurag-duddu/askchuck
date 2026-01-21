"""
Contextual enrichment for chunks using LLM.
Adds context prefixes to chunks for better retrieval (Anthropic's approach).
"""

import logging
import time
from typing import List

from groq import Groq

from src.utils.config import settings

logger = logging.getLogger(__name__)


class ContextualEnricher:
    """
    Adds contextual prefixes to chunks using Groq LLM.
    Based on Anthropic's contextual retrieval research.
    """

    # System prompt for context generation
    SYSTEM_PROMPT = """You are an expert at providing concise context for text chunks from academic papers on design methodology.

Your task: Given a chunk of text from a paper, provide a 2-3 sentence context that explains:
1. What document this chunk is from
2. What section or topic it discusses
3. How it relates to Charles Owen's Structured Planning methodology

The context should help someone understand what this chunk is about without reading the full document.
Use Owen's terminology correctly (Function, Design Factor, Information Structure, etc.).

Format: Just output the context sentences, no preamble."""

    def __init__(self):
        """Initialize the contextual enricher."""
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = settings.groq_model

    def enrich_chunk(self, chunk: dict) -> dict:
        """
        Add contextual prefix to a single chunk.

        Args:
            chunk: Chunk dictionary

        Returns:
            Chunk with enriched_text populated
        """
        # Skip if already enriched
        if chunk.get("enriched_text"):
            return chunk

        # Skip figure chunks (they're already self-contained)
        if chunk.get("level") == "figure":
            chunk["enriched_text"] = chunk["text"]
            return chunk

        try:
            # Generate context
            context = self._generate_context(chunk)

            # Prepend context to chunk text
            enriched = f"{context}\n\n{chunk['text']}"

            chunk["enriched_text"] = enriched

            logger.debug(f"Enriched chunk {chunk['chunk_id'][:30]}...")

        except Exception as e:
            logger.error(f"Failed to enrich chunk {chunk.get('chunk_id')}: {e}")
            # Fallback: use original text
            chunk["enriched_text"] = chunk["text"]

        return chunk

    def enrich_chunks_batch(
        self, chunks: List[dict], rate_limit_delay: float = 0.5
    ) -> List[dict]:
        """
        Enrich multiple chunks with rate limiting.

        Args:
            chunks: List of chunks to enrich
            rate_limit_delay: Delay between API calls (seconds)

        Returns:
            List of enriched chunks
        """
        logger.info(f"Enriching {len(chunks)} chunks")

        # Filter out figures (already self-contained)
        text_chunks = [c for c in chunks if c.get("level") != "figure"]
        figure_chunks = [c for c in chunks if c.get("level") == "figure"]

        logger.info(f"  {len(text_chunks)} text chunks to enrich")
        logger.info(f"  {len(figure_chunks)} figure chunks (skip enrichment)")

        # Enrich text chunks
        for i, chunk in enumerate(text_chunks):
            try:
                self.enrich_chunk(chunk)

                # Rate limiting
                if i < len(text_chunks) - 1:
                    time.sleep(rate_limit_delay)

            except Exception as e:
                logger.error(f"Error enriching chunk {i}: {e}")
                chunk["enriched_text"] = chunk["text"]  # Fallback
                continue

        # Set enriched_text for figures (use original)
        for chunk in figure_chunks:
            chunk["enriched_text"] = chunk["text"]

        return chunks

    def _generate_context(self, chunk: dict) -> str:
        """
        Generate context prefix for a chunk using LLM.

        Args:
            chunk: Chunk dictionary with metadata

        Returns:
            Context string
        """
        # Create user prompt with metadata
        user_prompt = self._create_user_prompt(chunk)

        # Call Groq API
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=150,
            temperature=0.3,
        )

        context = response.choices[0].message.content.strip()

        return context

    def _create_user_prompt(self, chunk: dict) -> str:
        """
        Create user prompt for context generation.

        Args:
            chunk: Chunk dictionary

        Returns:
            Prompt string
        """
        metadata = chunk.get("metadata", {})

        # Build prompt with available metadata
        prompt_parts = []

        prompt_parts.append("Provide 2-3 sentence context for this chunk:")
        prompt_parts.append("")

        # Document info
        doc_title = metadata.get("document_title", "Unknown document")
        prompt_parts.append(f"Document: {doc_title}")

        # Section info
        section = metadata.get("source_section")
        if section:
            prompt_parts.append(f"Section: {section}")

        # Owen terms present
        owen_terms = metadata.get("owen_terms", [])
        if owen_terms:
            prompt_parts.append(f"Owen terms: {', '.join(owen_terms[:5])}")

        prompt_parts.append("")
        prompt_parts.append("Chunk text:")
        prompt_parts.append(chunk["text"][:1000])  # Limit chunk text for prompt

        if len(chunk["text"]) > 1000:
            prompt_parts.append("...")

        return "\n".join(prompt_parts)


def enrich_chunk(chunk: dict) -> dict:
    """Convenience function to enrich a single chunk."""
    enricher = ContextualEnricher()
    return enricher.enrich_chunk(chunk)


def enrich_chunks(chunks: List[dict]) -> List[dict]:
    """Convenience function to enrich multiple chunks."""
    enricher = ContextualEnricher()
    return enricher.enrich_chunks_batch(chunks)
