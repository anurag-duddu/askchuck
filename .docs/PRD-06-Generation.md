# PRD-06: Generation

## Document Information

| Field | Value |
|-------|-------|
| PRD ID | PRD-06 |
| Version | v2.0 |
| Phase | 5 |
| Estimated Duration | 1.5 hours |
| Dependencies | PRD-05 (Retrieval Pipeline) |
| Owner | Developer |

**Key Changes from v1.0:**
- Updated from Llama 3.1 70B to **Llama 3.3 70B** (128K context window)
- Updated figure URLs from Supabase to **Cloudflare R2**
- Enhanced citation format: hybrid approach with chunk IDs in metadata
- Aligned with PRD-05 hierarchical retrieval (parent-child chunks)
- Aligned with PRD-04 flattened Pinecone metadata schema
- Conservative 8K token allocation (room to scale to 128K later)

---

## Objective

Build the generation layer that synthesizes coherent, accurate, and well-grounded responses from retrieved chunks. This phase creates the RAG chain that takes a user query, retrieves relevant context from the Pinecone hybrid index, constructs an optimized prompt, generates a response using Groq's **Llama 3.3 70B** model, and formats the output with proper citations and figure references. The generation layer must maintain fidelity to Owen's terminology while being accessible to users unfamiliar with Structured Planning methodology.

**The shift from v1.0:** We now use Llama 3.3 70B (128K context window) instead of Llama 3.1 70B (8K), leverage the hierarchical parent-child chunk structure from PRD-03/04, and display figures from Cloudflare R2 instead of Supabase.

---

## Background

The generation phase is where RAG systems succeed or fail at their core mission: providing accurate, helpful answers grounded in source documents. Several challenges make this particularly demanding for Owen's literature.

The first challenge is **terminology precision**. Owen's methodology uses terms like "Function," "Speculation," and "Mode" with precise meanings that differ from everyday usage. The generation model must use these terms correctly and consistently, never substituting general language when Owen's specific vocabulary applies.

The second challenge is **source fidelity**. Responses must be grounded in the retrieved context, not in the model's general knowledge about design thinking or systems theory. When the context doesn't fully answer a question, the model should acknowledge this rather than hallucinating plausible-sounding but unsourced content.

The third challenge is **figure integration**. Many of Owen's concepts are best understood visually—an Information Structure diagram conveys hierarchical relationships that would take paragraphs to describe. The generation layer must recognize when figures are relevant and incorporate them into responses with appropriate explanations.

The fourth challenge is **conversation continuity**. In multi-turn conversations, the model must maintain context from previous exchanges while avoiding the "lost in the middle" phenomenon where earlier context is forgotten.

The fifth challenge is **hierarchical context**. With parent-child chunk relationships from PRD-03, the generation layer must intelligently handle both precise child chunks (512 tokens) and broader parent chunks (2048 tokens) when constructing context.

---

## Functional Requirements

### FR-01: Prompt Construction

The system shall construct prompts that effectively guide the LLM to generate grounded, accurate responses.

**Acceptance Criteria:**
- System prompt establishes AskChuck persona and guidelines
- System prompt includes Owen terminology glossary
- User prompt includes retrieved context with clear formatting
- Conversation history is included for multi-turn support
- Prompt respects token limits while maximizing context (~8K conservatively)
- Context includes both child and parent chunks when retrieved via hierarchical expansion

### FR-02: Context Formatting

The system shall format retrieved chunks for optimal LLM consumption, respecting the hierarchical parent-child structure.

**Acceptance Criteria:**
- Chunks are clearly delineated with source attribution
- Parent vs child chunk level indicated when relevant
- Figure chunks are marked specially with image indicators
- Metadata (document title, section, chunk_level) is included
- Context is ordered by relevance (rerank score from Cohere)
- Duplicate or highly overlapping content is deduplicated
- Cloudflare R2 URLs used for figure display

### FR-03: Response Generation

The system shall generate responses using Groq's **Llama 3.3 70B** model.

**Acceptance Criteria:**
- Uses Llama 3.3 70B model (128K context window available)
- Conservative ~8K token usage (room to expand later)
- Appropriate temperature for factual responses (0.1-0.3)
- Respects max token limits for responses (~1500 tokens)
- Handles API errors gracefully with retries
- Streams responses for better UX (where supported)
- LangSmith tracing enabled for observability

### FR-04: Citation Generation

The system shall include source citations in responses using a hybrid format.

**Acceptance Criteria:**
- **Display format:** Citations reference documents and sections as [Document Title, Section]
- **Metadata format:** Response metadata includes chunk_ids for each source used
- Citation format: [Document Title, Section] (user-facing)
- Citations are placed inline near relevant claims
- All major claims are attributed to sources
- Chunk IDs stored in response metadata for debugging and traceability

### FR-05: Figure Integration

The system shall identify and include relevant figures in responses from Cloudflare R2.

**Acceptance Criteria:**
- Figures are referenced when visually relevant
- Figure captions and descriptions are provided
- **Figure URLs are Cloudflare R2 URLs** (r2_url field from metadata)
- Model explains what the figure shows
- Maximum 3 figures per response (prevent UI clutter)
- Figures prioritized by retrieval relevance score

### FR-06: Conversation Management

The system shall maintain conversation context across turns.

**Acceptance Criteria:**
- Previous messages are included in prompt (last 5 turns)
- Context window is managed to avoid truncation (~1K tokens for history)
- Conversation can be reset for new topics
- Follow-up questions are handled naturally
- Previous context informs retrieval for follow-up queries

### FR-07: Fallback Handling

The system shall gracefully handle cases where context is insufficient.

**Acceptance Criteria:**
- Model acknowledges when information is not in sources
- Suggests related topics that ARE covered
- Never fabricates Owen methodology content
- Offers to search for related information
- Provides helpful guidance on refining queries

---

## Technical Specification

### Generation Flow

```
┌─────────────────┐
│   User Query    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│      Retrieval Pipeline             │
│    (from PRD-05 v2.0)               │
│                                     │
│  - Pinecone hybrid search           │
│  - Parent-child expansion           │
│  - Cohere reranking                 │
│  - Figure retrieval                 │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│           Prompt Construction            │
│  ┌─────────────┐  ┌─────────────┐       │
│  │   System    │  │   Context   │       │
│  │   Prompt    │  │  Formatting │       │
│  │  + Glossary │  │ (Parent+Child)      │
│  └──────┬──────┘  └──────┬──────┘       │
│         │                │              │
│         └───────┬────────┘              │
│                 ▼                       │
│         ┌─────────────┐                 │
│         │    Full     │                 │
│         │   Prompt    │                 │
│         │   (~8K)     │                 │
│         └──────┬──────┘                 │
└────────────────┼────────────────────────┘
                 │
                 ▼
         ┌─────────────┐
         │    Groq     │
         │ Llama 3.3   │
         │  70B (128K) │
         └──────┬──────┘
                │
                ▼
┌─────────────────────────────────────────┐
│           Response Processing            │
│  ┌─────────────┐  ┌─────────────┐       │
│  │  Citation   │  │   Figure    │       │
│  │ Extraction  │  │  Matching   │       │
│  │ (Hybrid)    │  │ (R2 URLs)   │       │
│  └──────┬──────┘  └──────┬──────┘       │
│         │                │              │
│         └───────┬────────┘              │
│                 ▼                       │
│         ┌─────────────┐                 │
│         │   Final     │                 │
│         │  Response   │                 │
│         │+ chunk_ids  │                 │
│         └─────────────┘                 │
└─────────────────────────────────────────┘
```

### Token Budget Allocation

For Llama 3.3 70B with **128K context window** (using conservatively ~8K):

| Component | Token Allocation | Notes |
|-----------|-----------------|-------|
| System Prompt | ~800 tokens | AskChuck persona, guidelines |
| Owen Glossary | ~600 tokens | Key terminology definitions |
| Retrieved Context | ~4000 tokens | 5 chunks × ~800 tokens each (mix of parent/child) |
| Conversation History | ~1000 tokens | Last 5 turns, truncated if needed |
| User Query | ~100 tokens | Current question |
| Response Buffer | ~1500 tokens | Generated answer |
| **Total** | **~8000 tokens** | **Conservative usage (can scale to 128K later)** |

**Rationale for conservative allocation:**
- Proven to work from v1.0 design
- Fast generation times (<2 seconds)
- Leaves 120K tokens available for future expansion (long documents, extensive history)
- Can increase to ~20K or ~50K tokens if evaluation shows benefits

---

## Implementation Details

### File: src/generation/prompts.py

```python
"""
Prompt templates for AskChuck RAG generation.
Includes system prompts, context formatting, and response guidelines.
"""

from src.utils.owen_glossary import format_glossary_for_prompt, OWEN_GLOSSARY


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


# Template for formatting individual context chunks
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


def format_context_chunks(chunks: list[dict]) -> str:
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
                figure_url=metadata.get("r2_url", "")  # Cloudflare R2 URL
            )
        else:
            # Format as text chunk (parent or child)
            chunk_level = metadata.get("chunk_level", "unknown")

            # Mark if chunk references figures
            figure_marker = ""
            explicit_figures = metadata.get("explicit_figures", [])
            if explicit_figures:
                figure_marker = f"\n*[References: {', '.join(explicit_figures)}]*"

            formatted = CONTEXT_CHUNK_TEMPLATE.format(
                document_title=chunk.get("document_title", "Unknown Document"),
                section=metadata.get("section", ""),
                chunk_level=chunk_level.capitalize(),
                figure_marker=figure_marker,
                content=chunk.get("content", "")
            )

        formatted_parts.append(formatted)

    return "\n".join(formatted_parts)


def format_conversation_history(messages: list[dict], max_turns: int = 5) -> str:
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
    recent_messages = messages[-(max_turns * 2):]

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
    context_chunks: list[dict],
    conversation_history: list[dict] = None
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
        glossary=glossary,
        context=context,
        history=history
    )

    # Build user prompt
    user_prompt = USER_PROMPT_TEMPLATE.format(question=question)

    return system_prompt, user_prompt


# Prompt for handling insufficient context
INSUFFICIENT_CONTEXT_GUIDANCE = """
The retrieved context may not fully address this question. In your response:
1. Share what relevant information IS available in the context
2. Clearly state what aspects of the question cannot be answered from the sources
3. Suggest related topics from Owen's methodology that might be helpful
4. Do NOT make up information about Structured Planning
"""
```

### File: src/generation/rag_chain.py

```python
"""
Complete RAG chain for AskChuck.
Orchestrates retrieval, prompt construction, and generation.
"""

import logging
from typing import Optional, Generator

from groq import Groq
from langsmith import traceable

from src.retrieval.retrieval_pipeline import RetrievalPipeline, get_retrieval_pipeline
from src.generation.prompts import build_full_prompt
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
        retrieval_pipeline: RetrievalPipeline = None,
        model: str = "llama-3.3-70b-versatile",  # Llama 3.3 70B (128K context)
        temperature: float = 0.2,
        max_tokens: int = 1500
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

    @traceable(name="askchuck_query", run_type="chain")
    def query(
        self,
        question: str,
        conversation_history: list[dict] = None,
        include_figures: bool = True,
        top_k: int = 5
    ) -> dict:
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
        retrieval_result = self.retrieval.retrieve(
            query=question,
            top_k=top_k,
            include_figures=include_figures,
            expand_parents=True  # Use hierarchical expansion from PRD-05
        )

        all_chunks = retrieval_result.get("chunks", [])

        if not all_chunks:
            logger.warning("No relevant chunks found")
            return self._no_context_response(question)

        # Step 2: Build prompt (handles parent/child chunks + figures)
        system_prompt, user_prompt = build_full_prompt(
            question=question,
            context_chunks=all_chunks,
            conversation_history=conversation_history
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
            "chunks_used": len(all_chunks)
        }

    def _generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate response using Groq Llama 3.3 70B."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return f"I encountered an error generating a response. Please try again. (Error: {str(e)[:100]})"

    def stream_query(
        self,
        question: str,
        conversation_history: list[dict] = None,
        include_figures: bool = True,
        top_k: int = 5
    ) -> Generator[dict, None, None]:
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
        retrieval_result = self.retrieval.retrieve(
            query=question,
            top_k=top_k,
            include_figures=include_figures,
            expand_parents=True
        )

        all_chunks = retrieval_result.get("chunks", [])

        if not all_chunks:
            yield {"type": "token", "content": "I couldn't find relevant information in Owen's literature for this question."}
            yield {"type": "done"}
            return

        # Build prompt
        system_prompt, user_prompt = build_full_prompt(
            question=question,
            context_chunks=all_chunks,
            conversation_history=conversation_history
        )

        # Stream generation
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield {
                        "type": "token",
                        "content": chunk.choices[0].delta.content
                    }

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

    def _no_context_response(self, question: str) -> dict:
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
            "chunks_used": 0
        }

    def _extract_display_figures(self, all_chunks: list[dict]) -> list[dict]:
        """
        Extract figures for display in the response (Cloudflare R2 URLs).
        Maximum 3 figures to prevent UI clutter.
        """
        figures = []
        seen_urls = set()

        for chunk in all_chunks:
            if chunk.get("chunk_type") == "figure":
                metadata = chunk.get("metadata", {})
                url = metadata.get("r2_url")  # Cloudflare R2 URL

                if url and url not in seen_urls:
                    figures.append({
                        "url": url,
                        "caption": metadata.get("caption", ""),
                        "document": chunk.get("document_title", ""),
                        "figure_number": metadata.get("figure_number"),
                        "description": chunk.get("content", "")
                    })
                    seen_urls.add(url)

                    # Limit to 3 figures
                    if len(figures) >= 3:
                        break

        return figures

    def _build_sources_list(self, chunks: list[dict]) -> list[dict]:
        """
        Build deduplicated list of sources in [Document, Section] format.
        Includes chunk metadata for debugging.
        """
        sources = []
        seen = set()

        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            doc_title = chunk.get("document_title", "Unknown")
            section = metadata.get("section", "")
            key = (doc_title, section)

            if key not in seen:
                sources.append({
                    "display": f"[{doc_title}, {section}]",  # User-facing format
                    "document": doc_title,
                    "section": section,
                    "chunk_id": chunk.get("chunk_id"),
                    "chunk_level": metadata.get("chunk_level", "unknown")
                })
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


def ask(question: str, history: list[dict] = None) -> dict:
    """Convenience function to query AskChuck."""
    return get_rag_chain().query(question, conversation_history=history)
```

---

## Acceptance Criteria

| Criterion | Verification Method |
|-----------|-------------------|
| System prompt includes glossary | Inspect constructed prompt |
| Context chunks formatted with parent/child indicators | Inspect constructed prompt |
| Responses cite sources in [Document, Section] format | Check for inline citations |
| Chunk IDs included in response metadata | Verify response dict structure |
| Figures displayed with Cloudflare R2 URLs | Query about visual concepts |
| Maximum 3 figures per response | Count figures in results |
| Conversation history maintained (5 turns) | Multi-turn conversation test |
| Model acknowledges missing information | Query out-of-scope topic |
| Streaming works correctly | Test stream_query method |
| LangSmith traces recorded | Check LangSmith dashboard |
| Hierarchical chunks (parent/child) handled | Verify context formatting |

---

## Test Queries

**Basic factual (should cite sources with chunk IDs in metadata):**
- "What is a Design Factor?"
- "Explain the Abstraction Ladder concept"

**Visual concept (should include figures with R2 URLs, max 3):**
- "Show me an example of an Information Structure"
- "What does a Function Structure look like?"

**Multi-turn (should maintain context for 5 turns):**
- "What is a Speculation?" → "How does it relate to Design Factors?" → "Give me an example"

**Out of scope (should acknowledge honestly):**
- "What is Owen's opinion on Agile methodology?"
- "Compare Structured Planning to Design Sprints"

**Hierarchical chunks (should leverage parent context when needed):**
- "Explain the relationship between Structured Planning phases" (benefits from parent chunks)
- "What are the specific steps in Action Analysis?" (benefits from child chunks)

---

## Configuration Parameters

| Parameter | Default Value | Purpose | Tuning Guidance |
|-----------|--------------|---------|-----------------|
| `model` | `llama-3.3-70b-versatile` | Groq model ID | Llama 3.3 70B with 128K context window |
| `temperature` | 0.2 | Generation creativity | Lower (0.1-0.3) for factual, higher (0.5-0.7) for creative |
| `max_tokens` | 1500 | Response length | Increase for detailed explanations, decrease for concise answers |
| `top_k` | 5 | Chunks to retrieve | More chunks = more context but slower generation |
| `include_figures` | True | Retrieve figures | Disable for text-only queries |
| `max_turns_history` | 5 | Conversation history | Balance context continuity vs token budget |
| `max_figures` | 3 | Figure display limit | Prevent UI clutter while showing key visuals |

---

## Context Window Strategy

**Llama 3.3 70B specifications:**
- **Context window:** 128K tokens (vs 8K in Llama 3.1)
- **Current usage:** Conservative ~8K tokens
- **Future expansion:** Can scale to 20K-50K+ tokens if needed

**Conservative 8K allocation rationale:**
1. **Proven performance** from v1.0 design
2. **Fast generation** (<2 seconds typical)
3. **Room for growth** - 120K tokens available for future features:
   - Long-form document synthesis
   - Extensive conversation history
   - Multi-document comparison
   - Complex multi-step reasoning

**Expansion triggers:**
- Evaluation shows benefit from more context
- User feedback requests longer responses
- Complex queries require broader document coverage

---

## Next Steps

Once generation is working, proceed to **PRD-07: Frontend** to build the user interface with Next.js and authentication.
