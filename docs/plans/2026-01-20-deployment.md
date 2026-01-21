# PRD-09 Implementation Plan: Deployment

**Created:** 2026-01-20
**PRD Reference:** `.docs/PRD-09-Deployment.md` v2.0
**Status:** In Progress

---

## Objective

Deploy AskChuck RAG system with the current Streamlit + FastAPI architecture.

---

## Current Implementation vs. PRD Specification

**Current Implementation (PRD-01 through PRD-08):**
- ✅ FastAPI server (`src/api/server.py`) - Production-ready HTTP API
- ✅ Streamlit UI (`streamlit_app.py`) - Functional chat interface
- ✅ Pinecone index populated with 900 vectors
- ✅ Cloudflare R2 with figures
- ✅ RAG chain with streaming support
- ✅ Evaluation framework with golden dataset

**PRD-09 Specification:**
- Next.js frontend on Vercel
- FastAPI backend on Railway
- Supabase for chat persistence
- Clerk for authentication

---

## Practical Deployment Approach

### Phase 1: Deploy Current System (Immediate)

**Deliverable:** Working deployment of Streamlit + FastAPI

**Components:**
1. FastAPI backend deployed to Railway/Render
2. Streamlit UI running locally or on Streamlit Cloud
3. Documentation for deployment process
4. Environment variable templates
5. Docker configuration for containerized deployment

**Rationale:**
- FastAPI backend is production-ready and reusable
- Streamlit provides functional end-to-end system
- Can be deployed immediately for testing and feedback
- Maintains all RAG functionality

### Phase 2: Future Migration (When Ready)

**Deliverable:** Next.js frontend migration

**Reference:** `docs/NEXT_JS_ARCHITECTURE.md` provides complete migration guide

---

## Implementation Tasks

### Task 1: Create Deployment Documentation

**Acceptance Criteria:**
- Document FastAPI deployment to Railway/Render
- Document Streamlit local/cloud deployment
- Document Docker containerization
- Environment variable templates
- Production configuration guide

### Task 2: Create Docker Configuration

**Acceptance Criteria:**
- Dockerfile for FastAPI backend
- docker-compose.yml for local deployment
- Production-ready configuration
- Health check endpoints

### Task 3: Environment Variable Management

**Acceptance Criteria:**
- .env.example for backend
- Documentation of all required variables
- Security best practices
- No secrets in repository

### Task 4: Deployment Verification

**Acceptance Criteria:**
- Health check endpoints working
- API accessible via HTTPS
- Streaming endpoints functional
- LangSmith tracing operational

---

## Deployment Options

### Option A: Railway (Backend) + Streamlit Cloud

**Pros:**
- Free tiers available
- Auto-deployment from GitHub
- Simple configuration

**Cons:**
- Streamlit Cloud can be slow
- Limited customization

### Option B: Docker on VPS (DigitalOcean/Hetzner)

**Pros:**
- Full control
- Better performance
- Cost-effective for low traffic

**Cons:**
- Manual deployment
- Requires server management

### Option C: Railway (Backend) + Local Streamlit

**Pros:**
- Backend always available
- Local Streamlit for testing
- No hosting costs for UI

**Cons:**
- Streamlit not publicly accessible
- Manual startup required

---

## Files to Create

1. `Dockerfile` - FastAPI backend container
2. `docker-compose.yml` - Multi-container deployment
3. `.env.example` - Environment variable template
4. `docs/DEPLOYMENT.md` - Deployment guide
5. `docs/DEPLOYMENT_COMPLETE.md` - Completion documentation

---

## Target State

After completing PRD-09, the system will:
- ✅ Have deployable FastAPI backend
- ✅ Have documented deployment process
- ✅ Have containerization for production
- ✅ Have environment configuration templates
- ✅ Have health monitoring and observability
- 📋 (Future) Migrate to Next.js for production frontend

---

## Timeline

- Task 1: 30 minutes
- Task 2: 30 minutes
- Task 3: 15 minutes
- Task 4: 15 minutes

**Total:** ~1.5 hours

---

**Current Status:** Creating deployment documentation and Docker configuration
