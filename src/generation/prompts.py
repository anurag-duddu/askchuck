"""
Prompt templates for AskChuck RAG generation.
Includes system prompts, context formatting, and response guidelines.
"""

import re
from typing import List

from src.utils.owen_glossary import format_glossary_for_prompt


def _clean_document_title(title: str, metadata: dict = None) -> str:
    """
    Clean up document titles, removing technical artifacts.
    Falls back to filename-derived title if needed.
    """
    if not title:
        title = "Unknown Document"

    # Check for PostScript/technical artifacts
    title_lower = title.lower()
    is_invalid = (
        ("pmu" in title_lower and ".out" in title_lower)
        or (title.startswith("(") and "composite" in title_lower)
        or len(title.strip()) < 5
    )

    if is_invalid:
        # Try to get clean title from metadata
        if metadata:
            # Try pdf_filename
            pdf_filename = metadata.get("pdf_filename", "")
            if pdf_filename:
                # Convert filename to title: "Design-thinking-what-it-is.pdf" -> "Design Thinking What It Is"
                name = pdf_filename.rsplit(".", 1)[0]  # Remove extension
                name = re.sub(r"[_-]", " ", name)  # Replace separators
                name = re.sub(
                    r"owen\s*", "", name, flags=re.IGNORECASE
                )  # Remove "owen" prefix
                return name.strip().title()

        return "Owen's Paper"

    return title


# Core system prompt establishing AskChuck's identity and behavior
SYSTEM_PROMPT_TEMPLATE = """You are AskChuck, an expert assistant specializing in Charles Owen's Structured Planning methodology from IIT Institute of Design.

## Your Role
You help students, researchers, and practitioners understand Owen's systematic approach to human-centered innovation. You answer questions by drawing on Owen's published papers and articles, always grounding your responses in the source material.

## Owen's Key Terminology
Use these terms precisely as Owen defined them:

{glossary}

## Response Guidelines

1. **ONLY use the provided context.** Every statement must be directly supported by the retrieved passages. If you cannot cite a source [1], [2], [3] for a claim, do not make it. Never use general design knowledge to supplement the context.

2. **Use Owen's terminology correctly.** When discussing Structured Planning concepts, use the specific terms Owen uses (Function, Design Factor, Speculation, etc.) rather than paraphrasing with general language.

3. **Cite your sources.** Use numbered citations like [1], [2], [3] that correspond to the source numbers in the context below. Place citations inline, near the relevant statement. Do NOT include document filenames or technical IDs in your response.

4. **Explain figures when relevant.** If a figure is provided in the context, describe what it shows and how it relates to the question. Figures are marked with [FIGURE] in the context and have Cloudflare R2 URLs for display.

5. **Be helpful and educational.** Explain concepts clearly, using examples from Owen's work when available. Connect abstract ideas to concrete applications.

6. **Be precise about limitations.** If specific information is missing from the context, state exactly what is missing and what IS available in the sources. Do not speculate or use general knowledge to fill gaps. Example: "The sources don't explain [X], but they do cover [Y] in [1]."

7. **Maintain conversational flow.** In multi-turn conversations, refer back to previous context naturally. Use the conversation history to understand follow-up questions.

8. **Leverage hierarchical context.** The context includes both focused passages (child chunks, ~512 tokens) and broader context (parent chunks, ~2048 tokens). Use both for comprehensive understanding.

## What NOT to Do

- Do not make up Owen methodology concepts not present in the context
- Do not use general design thinking knowledge to fill gaps in Owen's specific methodology
- Do not provide lengthy quotes; paraphrase and cite instead
- Do not ignore figures when they're relevant to the question
- Do not claim certainty about topics not covered in the retrieved context

## CRITICAL: Faithfulness Requirement

You MUST ONLY use information explicitly stated in the Retrieved Context below.

**Rules:**
- Every factual claim must be traceable to a specific source [1], [2], [3]
- If the context lacks information about ANY aspect of the question, state: "The provided sources don't contain information about [specific aspect]"
- Do NOT use general knowledge about design thinking or Owen's methodology beyond what's in the context
- Do NOT infer, extrapolate, or fill gaps with assumptions
- When uncertain, explicitly cite the source that supports your statement

If you cannot cite a source for a claim, do not make the claim.

## Retrieved Context
The following passages are from Owen's literature and are relevant to the user's question. Use them to formulate your response.

{context}

## Conversation History
{history}
"""


# Template for formatting individual text chunks
CONTEXT_CHUNK_TEMPLATE = """
---
**[Source {source_number}]** {document_title}
**Section:** {section}
**Level:** {chunk_level}{figure_marker}

{content}
---
"""


# Template for figure chunks
FIGURE_CHUNK_TEMPLATE = """
---
**[FIGURE]**
**Source:** {document_title}
**Figure {figure_number}:** {caption}

{description}

*Figure URL (Cloudflare R2): {figure_url}*
---
"""


# User message template
USER_PROMPT_TEMPLATE = """Based on the context from Owen's literature provided above, please answer this question:

{question}

Remember to cite sources using numbered references like [1], [2], [3] that match the source numbers above. Reference relevant figures if applicable."""


# Prompt for handling insufficient context
INSUFFICIENT_CONTEXT_GUIDANCE = """
The retrieved context may not fully address this question. In your response:
1. Share what relevant information IS available in the context
2. Clearly state what aspects of the question cannot be answered from the sources
3. Suggest related topics from Owen's methodology that might be helpful
4. Do NOT make up information about Structured Planning
"""


def _get_source_key(chunk: dict) -> tuple:
    """
    Get the grouping key for a chunk.
    Chunks with same (document_title, section) are considered the same source.
    """
    metadata = chunk.get("metadata", {})
    doc_title = (
        chunk.get("document_title") or metadata.get("document_title") or "Unknown"
    )
    section = chunk.get("section") or metadata.get("source_section") or ""
    return (doc_title, section)


def group_chunks_by_source(chunks: List[dict]) -> List[tuple]:
    """
    Group chunks by (document_title, section) and assign source numbers.

    Returns list of tuples: (source_number, source_key, list_of_chunks)
    This ensures LLM citation numbers match the deduplicated sources list.
    """
    from collections import OrderedDict

    # Group chunks by source key, preserving order of first occurrence
    grouped = OrderedDict()
    for chunk in chunks:
        key = _get_source_key(chunk)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(chunk)

    # Convert to list with source numbers (1-indexed)
    result = []
    for idx, (key, chunk_list) in enumerate(grouped.items(), start=1):
        result.append((idx, key, chunk_list))

    return result


def format_context_chunks(chunks: List[dict]) -> str:
    """
    Format retrieved chunks for inclusion in the prompt.
    Handles both text chunks (parent/child) and figure chunks.

    IMPORTANT: Groups chunks by (document, section) BEFORE assigning numbers.
    This ensures citation numbers [1], [2], [3] match the deduplicated sources
    shown in the UI. Multiple chunks from the same source share one number.

    Args:
        chunks: List of chunk dictionaries from retrieval pipeline

    Returns:
        Formatted string of all chunks
    """
    formatted_parts = []

    # Separate text chunks and figure chunks
    text_chunks = [c for c in chunks if c.get("chunk_type") != "figure"]
    figure_chunks = [c for c in chunks if c.get("chunk_type") == "figure"]

    # Group text chunks by source and format with consistent source numbers
    grouped_sources = group_chunks_by_source(text_chunks)

    for source_num, (doc_title, section), chunk_list in grouped_sources:
        # Clean document title
        clean_title = _clean_document_title(
            doc_title, chunk_list[0].get("metadata", {})
        )

        # Combine content from all chunks in this source group
        combined_content = []
        figure_refs = set()
        chunk_levels = set()

        for chunk in chunk_list:
            metadata = chunk.get("metadata", {})
            chunk_levels.add(chunk.get("chunk_level", "unknown"))

            # Collect figure references
            explicit_figures = metadata.get("explicit_figures", [])
            if explicit_figures:
                if isinstance(explicit_figures, list):
                    figure_refs.update(explicit_figures)
                elif isinstance(explicit_figures, str):
                    figure_refs.add(explicit_figures)

            content = chunk.get("content", "")
            if content:
                combined_content.append(content)

        # Build figure marker
        figure_marker = ""
        if figure_refs:
            figure_marker = f"\n*[References: {', '.join(sorted(figure_refs))}]*"

        # Determine chunk level display (combine if multiple)
        level_display = ", ".join(sorted(l.capitalize() for l in chunk_levels))

        formatted = CONTEXT_CHUNK_TEMPLATE.format(
            source_number=source_num,
            document_title=clean_title,
            section=section,
            chunk_level=level_display,
            figure_marker=figure_marker,
            content="\n\n".join(combined_content),
        )
        formatted_parts.append(formatted)

    # Format figure chunks (not grouped, each figure is unique)
    for chunk in figure_chunks:
        metadata = chunk.get("metadata", {})
        formatted = FIGURE_CHUNK_TEMPLATE.format(
            document_title=chunk.get("document_title", "Unknown Document"),
            figure_number=metadata.get("figure_number", "?"),
            caption=metadata.get("caption", ""),
            description=chunk.get("content", ""),
            figure_url=metadata.get("figure_url", ""),
        )
        formatted_parts.append(formatted)

    return "\n".join(formatted_parts)


def format_conversation_history(messages: List[dict], max_turns: int = 5) -> str:
    """
    Format conversation history for inclusion in prompt.

    Args:
        messages: List of message dicts with 'role' and 'content'
        max_turns: Maximum number of previous turns to include (each turn = user + assistant)

    Returns:
        Formatted conversation history string
    """
    if not messages:
        return "*No previous conversation*"

    # Take last N turns (each turn = user + assistant pair)
    recent_messages = messages[-(max_turns * 2) :]

    formatted_parts = []
    for msg in recent_messages:
        role = msg.get("role", "user").capitalize()
        content = msg.get("content", "")

        # Truncate very long messages
        if len(content) > 500:
            content = content[:500] + "..."

        formatted_parts.append(f"**{role}:** {content}")

    return "\n\n".join(formatted_parts)


def build_full_prompt(
    question: str,
    context_chunks: List[dict],
    conversation_history: List[dict] = None,
) -> tuple[str, str]:
    """
    Build the complete prompt for generation.

    Args:
        question: The user's question
        context_chunks: Retrieved chunks from the retrieval pipeline (PRD-05)
        conversation_history: Previous messages in the conversation

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    # Format glossary (abbreviated for token efficiency)
    glossary = format_glossary_for_prompt()

    # Format context (handles parent/child chunks and figures)
    context = format_context_chunks(context_chunks)

    # Format history
    history = format_conversation_history(conversation_history or [])

    # Build system prompt
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        glossary=glossary, context=context, history=history
    )

    # Build user prompt
    user_prompt = USER_PROMPT_TEMPLATE.format(question=question)

    return system_prompt, user_prompt
