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
        """Initialize the query expander."""
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = settings.groq_model  # llama-3.3-70b-versatile

    def expand_query(self, query: str, max_expansions: int = 3) -> str:
        """
        Expand query with related Owen terms.

        Args:
            query: The original user query
            max_expansions: Maximum number of related terms to add

        Returns:
            Expanded query string
        """
        # Build prompt with glossary (top 20 most common terms)
        glossary_items = list(OWEN_GLOSSARY.items())[:20]
        glossary_text = "\n".join(
            [
                f"- {term}: {info['definition'][:100]}..."
                for term, info in glossary_items
            ]
        )

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
                max_tokens=50,
            )

            expansion_text = response.choices[0].message.content.strip()

            if expansion_text == "NONE" or not expansion_text:
                logger.debug(f"No expansion terms found for: {query}")
                return query

            # Parse comma-separated terms
            terms = [t.strip() for t in expansion_text.split(",") if t.strip()]

            if not terms:
                return query

            # Create expanded query
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
