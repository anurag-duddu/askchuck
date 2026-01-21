# PRD-07: Frontend & API Implementation Plan

**Goal:** Create working frontend interface for AskChuck

**Approach:** FastAPI server + Streamlit UI (practical) + Next.js documentation (future)

**Rationale:** Next.js frontend (PRD v2.0) is a substantial separate project requiring external services (Clerk, Supabase, Vercel). For immediate functionality and to continue progress through remaining PRDs, we'll create:
1. FastAPI server exposing RAG chain as API
2. Streamlit UI for working prototype
3. Architecture docs for future Next.js implementation

---

## Task 1: Create FastAPI Server

**Files:**
- Create: `src/api/server.py`
- Create: `src/api/__init__.py`
- Create: `src/api/models.py` (Pydantic request/response models)

**Implementation:**
Expose RAG chain as HTTP API with streaming support

**Steps:**
1. Create FastAPI application
2. Add CORS middleware for frontend access
3. Create `/query` endpoint (non-streaming)
   - POST with question, session_id, conversation_history
   - Returns full response with answer, sources, figures, chunk_ids
4. Create `/stream_query` endpoint (SSE streaming)
   - POST with same params
   - Streams tokens in real-time via Server-Sent Events
   - Returns metadata at end
5. Create `/health` endpoint for monitoring
6. Add error handling and logging
7. Use Pydantic models for validation

**Verification:**
```bash
# Start server
python -m uvicorn src.api.server:app --reload

# Test endpoints
curl -X POST http://localhost:8000/query -H "Content-Type: application/json" -d '{"question": "What is a Design Factor?"}'
curl -X POST http://localhost:8000/stream_query -H "Content-Type: application/json" -d '{"question": "What is VTCON?"}'
```

**Commit:** `feat: add FastAPI server for RAG chain`

---

## Task 2: Create Streamlit UI

**Files:**
- Create: `streamlit_app.py` (root level)
- Create: `src/ui/streamlit_utils.py` (helper functions)

**Implementation:**
Build simple, functional chat interface with Streamlit

**Steps:**
1. Create main Streamlit app
2. Add session state for conversation history
3. Create chat interface with st.chat_message
4. Display user and assistant messages
5. Add input field for questions
6. Call RAG chain directly (or via FastAPI)
7. Display sources in expander
8. Display figures if present
9. Add new chat button
10. Style with custom CSS

**Verification:**
```bash
streamlit run streamlit_app.py
# Open browser, test chat interface
```

**Commit:** `feat: add Streamlit UI for AskChuck`

---

## Task 3: Add Streaming Support to Streamlit

**Files:**
- Update: `streamlit_app.py`

**Implementation:**
Use st.write_stream() for real-time token display

**Steps:**
1. Create generator function from stream_query
2. Use st.write_stream() to display tokens
3. Show loading spinner during retrieval
4. Display sources after streaming completes

**Verification:**
```bash
streamlit run streamlit_app.py
# Test streaming display
```

**Commit:** `feat: add streaming support to Streamlit UI`

---

## Task 4: Document Next.js Architecture

**Files:**
- Create: `docs/NEXT_JS_ARCHITECTURE.md`

**Content:**
- Full Next.js architecture from PRD-07
- Directory structure
- Key component implementations
- Supabase schema
- Clerk integration steps
- Deployment guide for Vercel

**Commit:** `docs: add Next.js frontend architecture`

---

## Task 5: Create Deployment Scripts

**Files:**
- Create: `scripts/run_api.py` (runs FastAPI server)
- Create: `scripts/run_streamlit.py` (runs Streamlit UI)
- Update: `README.md` with usage instructions

**Commit:** `docs: add deployment and usage instructions`

---

## Task 6: Documentation

**Files:**
- Create: `docs/FRONTEND_COMPLETE.md`

**Content:**
- FastAPI server overview
- Streamlit UI overview
- API endpoint documentation
- Usage examples
- Next.js migration path

**Commit:** `docs: add frontend completion summary`

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| ✅ FastAPI server runs | uvicorn starts without errors |
| ✅ /query endpoint works | Returns complete response |
| ✅ /stream_query SSE works | Streams tokens in real-time |
| ✅ Streamlit UI displays | Chat interface loads |
| ✅ Streamlit shows responses | Q&A works end-to-end |
| ✅ Streaming in Streamlit | Tokens appear in real-time |
| ✅ Sources displayed | Expandable source section |
| ✅ Figures displayed | Images shown if available |
| ✅ Next.js docs complete | Architecture documented |
| ✅ Deployment scripts | Easy to run |

---

## Notes

- **FastAPI:** Python-native, fast, auto-generates OpenAPI docs
- **Streamlit:** Quick to build, good for prototypes, works immediately
- **Next.js:** Production-grade but requires separate project and services
- **Migration path:** FastAPI backend + Next.js frontend later
- **Current approach:** Functional system NOW, upgrade path clear

---

## Dependencies

**New packages:**
- `fastapi>=0.104.0` - API framework
- `uvicorn[standard]>=0.24.0` - ASGI server
- `sse-starlette>=1.6.0` - SSE support for FastAPI
- `streamlit>=1.29.0` - Already in requirements.txt

**From PRD-06:**
- `src/generation/rag_chain.py` - AskChuckRAG class
