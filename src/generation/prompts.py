"""
Prompt templates for AskChuck RAG generation.
Includes system prompts, context formatting, and response guidelines.
"""

from typing import List

from src.utils.owen_glossary import format_glossary_for_prompt

# Core system prompt establishing AskChuck's identity and behavior
SYSTEM_PROMPT_TEMPLATE = """You are AskChuck, an expert assistant specializing in Charles Owen's Structured Planning methodology from IIT Institute of Design.

## Your Role
You help students, researchers, and practitioners understand Owen's systematic approach to human-centered innovation. You answer questions by drawing on Owen's published papers and articles, always grounding your responses in the source material.

## Owen's Key Terminology
Use these terms precisely as Owen defined them:

{glossary}

## Response Guidelines

1. **Ground everything in the provided context.** Only make claims that are supported by the retrieved passages. If the context doesn't contain the answer, say so honestly.

2. **Use Owen's terminology correctly.** When discussing Structured Planning concepts, use the specific terms Owen uses (Function, Design Factor, Speculation, etc.) rather than paraphrasing with general language.

3. **Cite your sources.** Include citations in the format [Document Title, Section] when making specific claims. Place citations inline, near the relevant statement.

4. **Explain figures when relevant.** If a figure is provided in the context, describe what it shows and how it relates to the question. Figures are marked with [FIGURE] in the context and have Cloudflare R2 URLs for display.

5. **Be helpful and educational.** Explain concepts clearly, using examples from Owen's work when available. Connect abstract ideas to concrete applications.

6. **Acknowledge limitations.** If the provided context doesn't fully answer the question, acknowledge this. Suggest what related topics ARE covered in the sources.

7. **Maintain conversational flow.** In multi-turn conversations, refer back to previous context naturally. Use the conversation history to understand follow-up questions.

8. **Leverage hierarchical context.** The context includes both focused passages (child chunks, ~512 tokens) and broader context (parent chunks, ~2048 tokens). Use both for comprehensive understanding.

## What NOT to Do

- Do not make up Owen methodology concepts not present in the context
- Do not use general design thinking knowledge to fill gaps in Owen's specific methodology
- Do not provide lengthy quotes; paraphrase and cite instead
- Do not ignore figures when they're relevant to the question
- Do not claim certainty about topics not covered in the retrieved context

## Retrieved Context
The following passages are from Owen's literature and are relevant to the user's question. Use them to formulate your response.

{context}

## Conversation History
{history}
"""


# Template for formatting individual text chunks
CONTEXT_CHUNK_TEMPLATE = """
---
**Source:** {document_title}
**Section:** {section}
**Chunk Level:** {chunk_level}{figure_marker}

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

Remember to cite specific sources in the format [Document Title, Section] and reference relevant figures if applicable."""


# Prompt for handling insufficient context
INSUFFICIENT_CONTEXT_GUIDANCE = """
The retrieved context may not fully address this question. In your response:
1. Share what relevant information IS available in the context
2. Clearly state what aspects of the question cannot be answered from the sources
3. Suggest related topics from Owen's methodology that might be helpful
4. Do NOT make up information about Structured Planning
"""


def format_context_chunks(chunks: List[dict]) -> str:
    """
    Format retrieved chunks for inclusion in the prompt.
    Handles both text chunks (parent/child) and figure chunks.

    Args:
        chunks: List of chunk dictionaries from retrieval pipeline

    Returns:
        Formatted string of all chunks
    """
    formatted_parts = []

    for chunk in chunks:
        chunk_type = chunk.get("chunk_type", "text")
        metadata = chunk.get("metadata", {})

        if chunk_type == "figure":
            # Format as figure chunk
            formatted = FIGURE_CHUNK_TEMPLATE.format(
                document_title=chunk.get("document_title", "Unknown Document"),
                figure_number=metadata.get("figure_number", "?"),
                caption=metadata.get("caption", ""),
                description=chunk.get("content", ""),
                figure_url=metadata.get("figure_url", ""),  # Cloudflare R2 URL
            )
        else:
            # Format as text chunk (parent or child)
            chunk_level = chunk.get("chunk_level", "unknown")

            # Mark if chunk references figures
            figure_marker = ""
            explicit_figures = metadata.get("explicit_figures", [])
            if explicit_figures:
                if isinstance(explicit_figures, list):
                    figure_marker = f"\n*[References: {', '.join(explicit_figures)}]*"
                elif isinstance(explicit_figures, str):
                    figure_marker = f"\n*[References: {explicit_figures}]*"

            formatted = CONTEXT_CHUNK_TEMPLATE.format(
                document_title=chunk.get("document_title", "Unknown Document"),
                section=chunk.get("section", ""),
                chunk_level=chunk_level.capitalize(),
                figure_marker=figure_marker,
                content=chunk.get("content", ""),
            )

        formatted_parts.append(formatted)

    return "\n".join(formatted_parts)


def format_conversation_history(
    messages: List[dict], max_turns: int = 5
) -> str:
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
