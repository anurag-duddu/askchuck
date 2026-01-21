# PRD-06: Generation Chain Implementation Plan

**Goal:** Build RAG generation layer with Groq Llama 3.3 70B

**Architecture:** Retrieval (PRD-05) + Prompt Construction + Llama 3.3 70B Generation

**Tech Stack:** Groq Llama 3.3 70B (128K context), LangSmith tracing

---

## Task 1: Create Owen Glossary Formatting

**Files:**
- Update: `src/utils/owen_glossary.py`

**Implementation:**
Add helper function to format glossary for prompt inclusion

**Steps:**
1. Create `format_glossary_for_prompt()` function
2. Format top 15-20 terms for token efficiency
3. Return formatted string for system prompt
4. Include term, definition, examples

**Verification:**
```python
from src.utils.owen_glossary import format_glossary_for_prompt
glossary = format_glossary_for_prompt()
print(glossary[:200])  # Should show formatted terms
```

**Commit:** `feat: add glossary formatting for prompts`

---

## Task 2: Create Prompt Templates

**Files:**
- Create: `src/generation/prompts.py`
- Create: `src/generation/__init__.py`

**Implementation:**
Build prompt templates and formatting functions

**Steps:**
1. Create SYSTEM_PROMPT_TEMPLATE with AskChuck persona
2. Include Owen glossary placeholder
3. Create CONTEXT_CHUNK_TEMPLATE for text chunks
4. Create FIGURE_CHUNK_TEMPLATE for figures (R2 URLs)
5. Create USER_PROMPT_TEMPLATE
6. Implement `format_context_chunks()` function
   - Handle text chunks (parent/child)
   - Handle figure chunks with Cloudflare R2 URLs
   - Mark chunk levels and sections
7. Implement `format_conversation_history()`
   - Limit to last 5 turns
   - Truncate long messages
8. Implement `build_full_prompt()`
   - Assemble system + user prompts
   - Insert glossary, context, history

**Verification:**
```python
from src.generation.prompts import build_full_prompt
system, user = build_full_prompt(
    question="What is a Design Factor?",
    context_chunks=mock_chunks,
    conversation_history=[]
)
print(f"System prompt length: {len(system)}")
print(f"User prompt length: {len(user)}")
```

**Commit:** `feat: add prompt templates and formatting`

---

## Task 3: Create RAG Chain

**Files:**
- Create: `src/generation/rag_chain.py`

**Implementation:**
Main RAG chain orchestrating retrieval + generation

**Steps:**
1. Create AskChuckRAG class
2. Initialize with RetrievalPipeline (from PRD-05)
3. Initialize Groq client with Llama 3.3 70B
4. Implement `query()` method:
   - Step 1: Retrieve chunks via PRD-05 pipeline
   - Step 2: Build prompt with context/history
   - Step 3: Generate response with Groq
   - Step 4: Extract figures (R2 URLs)
   - Step 5: Build sources list (hybrid format)
   - Return dict with answer, sources, chunk_ids, figures
5. Implement `_generate()` helper
   - Call Groq chat completions API
   - Handle errors gracefully
6. Implement `stream_query()` method
   - Stream tokens for better UX
   - Yield metadata at end
7. Implement `_no_context_response()`
8. Implement `_extract_display_figures()` (max 3)
9. Implement `_build_sources_list()` (hybrid format)
10. Add LangSmith @traceable decorator
11. Add global instance pattern

**Verification:**
```python
from src.generation.rag_chain import AskChuckRAG
rag = AskChuckRAG()
result = rag.query("What is a Design Factor?")
print(result["answer"][:200])
print(f"Sources: {len(result['sources'])}")
print(f"Chunk IDs: {result['chunk_ids']}")
```

**Commit:** `feat: add complete RAG chain with streaming`

---

## Task 4: Create CLI Testing Script

**Files:**
- Create: `scripts/test_generation.py`

**Implementation:**
CLI for testing RAG chain with sample queries

**Steps:**
1. Create test script with argparse
2. Add test queries from PRD:
   - Basic factual
   - Visual concepts (figures)
   - Multi-turn conversations
   - Out of scope
   - Hierarchical chunks
3. Options for:
   - Custom query
   - Streaming vs non-streaming
   - Top-k configuration
   - Include/exclude figures
4. Display formatted responses
5. Show sources, chunk IDs, figures
6. Test conversation flow

**Verification:**
```bash
python scripts/test_generation.py --query "What is a Design Factor?"
python scripts/test_generation.py --query "Show Information Structure" --stream
python scripts/test_generation.py --test-all
```

**Commit:** `feat: add generation testing CLI script`

---

## Task 5: Create Verification Script

**Files:**
- Create: `scripts/verify_generation.py`

**Implementation:**
Comprehensive generation verification

**Steps:**
1. Create verification script
2. Test basic query and response generation
3. Test source citations in [Document, Section] format
4. Test chunk IDs in metadata
5. Test figure integration (R2 URLs, max 3)
6. Test conversation history (5 turns)
7. Test fallback for no context
8. Test streaming functionality
9. Verify prompt construction
10. Report pass/fail statistics

**Verification:**
```bash
python scripts/verify_generation.py
# Should test all generation features
```

**Commit:** `feat: add generation verification script`

---

## Task 6: Documentation

**Files:**
- Create: `docs/GENERATION_COMPLETE.md`

**Content:**
- Component overview
- Prompt structure explanation
- RAG chain flow
- Citation format (hybrid approach)
- Figure integration (R2 URLs)
- Token budget breakdown
- Usage examples
- Testing queries
- Acceptance criteria checklist

**Commit:** `docs: add generation completion summary`

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| ✅ System prompt includes glossary | Check formatted prompt |
| ✅ Context formatted with parent/child | Verify chunk templates |
| ✅ Citations in [Document, Section] | Test factual query |
| ✅ Chunk IDs in metadata | Check response dict |
| ✅ Figures with R2 URLs | Test visual query |
| ✅ Max 3 figures per response | Verify figure limit |
| ✅ Conversation history (5 turns) | Multi-turn test |
| ✅ Fallback for missing info | Out-of-scope query |
| ✅ Streaming works | Test stream_query |
| ✅ LangSmith tracing | Check dashboard |

---

## Notes

- **Model:** Llama 3.3 70B (128K context window)
- **Conservative usage:** ~8K tokens (room to scale to 128K later)
- **Temperature:** 0.2 (factual responses)
- **Max tokens:** 1500 (responses)
- **Citation format:** Hybrid - display as [Doc, Section], store chunk_ids
- **Figures:** Cloudflare R2 URLs, max 3 per response
- **Streaming:** Use for better UX in frontend
- **LangSmith:** Enable for observability

---

## Dependencies

**From PRD-05:**
- `src/retrieval/retrieval_pipeline.py` - RetrievalPipeline

**From PRD-03:**
- `src/utils/owen_glossary.py` - OWEN_GLOSSARY

**New dependencies:**
- `langsmith` package (already in requirements.txt)
- Groq API for Llama 3.3 70B
