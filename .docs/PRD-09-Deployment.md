# PRD-09: Deployment

## Document Information

| Field | Value |
|-------|-------|
| PRD ID | PRD-09 |
| Version | v2.0 |
| Phase | 8 |
| Estimated Duration | 2-3 hours |
| Dependencies | PRD-07 (Frontend), All prior phases |
| Owner | Developer |

**Key Changes from v1.0:**
- Complete architecture shift from Streamlit Cloud to Next.js + Vercel + FastAPI + Railway
- Frontend: Next.js 14 deployed to Vercel (free tier, auto-deploy)
- Backend: FastAPI deployed to Railway (free tier, always-on)
- Database: Supabase Postgres setup with RLS policies
- Authentication: Clerk configuration and integration
- Storage: Cloudflare R2 bucket configuration
- Vector DB: Pinecone Serverless (no deployment needed, API-only)
- Split deployment: Frontend and backend deployed separately

---

## Objective

Deploy AskChuck as a production-grade web application with split frontend (Next.js on Vercel) and backend (FastAPI on Railway) architecture. The deployment leverages free tiers across all services, provides auto-deployment from GitHub, and enables public access via HTTPS URLs. Upon completion, users can access AskChuck through their browser, authenticate via Clerk, engage in persistent chat sessions stored in Supabase, and receive RAG-powered responses with figure display from Cloudflare R2.

---

## Background

AskChuck uses a modern split-architecture deployment strategy with separate frontend and backend services. This approach provides better scalability, independent deployment cycles, and clear separation of concerns compared to monolithic application hosting.

### Architecture Overview

**Frontend (Next.js on Vercel):**
- Server-side rendering for SEO and performance
- Clerk authentication integration
- Supabase Postgres queries for chat session management
- Proxies streaming requests to FastAPI backend
- Auto-deploys from GitHub on push to main branch
- Free tier: 100GB bandwidth, edge functions, unlimited deployments

**Backend (FastAPI on Railway):**
- Python RAG chain orchestration
- Pinecone hybrid search queries
- Voyage AI embeddings, Cohere reranking
- Groq Llama 3.3 70B generation
- Server-Sent Events (SSE) streaming support
- LangSmith tracing for observability
- Auto-deploys from GitHub on push to main branch
- Free tier: $5/month credit, 512MB RAM, always-on

**Data Services (Serverless):**
- **Pinecone:** Vector index already populated during PRD-04, API-only access
- **Cloudflare R2:** Figure storage with public HTTPS URLs
- **Supabase Postgres:** Chat sessions and messages with row-level security
- **Clerk:** Authentication provider with session management

### Deployment Philosophy

This deployment prioritizes zero/minimal cost operation while maintaining production-grade reliability. All services remain within generous free tiers, and the split architecture allows each component to scale independently. The frontend serves static assets from Vercel's global CDN while the backend runs continuously on Railway, eliminating cold start latency for RAG queries.

### Key Considerations

**Secrets Management:**
- Vercel manages frontend secrets (Clerk keys, Supabase URL, backend API URL)
- Railway manages backend secrets (Groq, Voyage AI, Pinecone, Cohere, Cloudflare R2, LangSmith)
- No secrets committed to repository

**CORS Configuration:**
- Backend must allow requests from Vercel frontend domain
- Cloudflare R2 must allow requests from Vercel domain for figure display

**Environment Variables:**
- Frontend: NEXT_PUBLIC_* variables exposed to browser, private variables server-only
- Backend: All secrets server-side only

---

## Functional Requirements

### FR-01: Frontend Deployment (Vercel)

The Next.js frontend shall be deployed to Vercel with proper configuration.

**Acceptance Criteria:**
- Next.js app builds successfully
- Environment variables configured in Vercel dashboard
- Clerk authentication integration working
- Supabase client connection established
- Backend API URL configured
- Auto-deploy from GitHub enabled
- Public URL accessible via HTTPS
- SSE streaming from backend functional

### FR-02: Backend Deployment (Railway)

The FastAPI backend shall be deployed to Railway with proper configuration.

**Acceptance Criteria:**
- FastAPI app starts without errors
- All Python dependencies installed
- Environment variables configured in Railway dashboard
- Health check endpoint responds
- CORS configured to allow Vercel domain
- RAG chain initializes successfully
- SSE streaming endpoint functional
- Auto-deploy from GitHub enabled

### FR-03: Pinecone Configuration

The Pinecone vector index shall be accessible from deployed backend.

**Acceptance Criteria:**
- Pinecone API key configured in Railway
- Index "askchuck" is populated with ~900 vectors
- Hybrid search queries return results
- Query latency acceptable (<1s)

### FR-04: Cloudflare R2 Configuration

Figure storage shall be configured for public access.

**Acceptance Criteria:**
- R2 bucket created and populated with figures
- Public access enabled for figure URLs
- CORS configured to allow Vercel domain
- R2 credentials configured in Railway
- Figure URLs resolve correctly in frontend

### FR-05: Supabase Configuration

Database shall be configured with schema and security policies.

**Acceptance Criteria:**
- Database tables created (chat_sessions, chat_messages)
- Row-level security (RLS) policies applied
- Supabase URL and keys configured in Vercel
- Frontend can query and insert data
- User data isolated by Clerk user_id

### FR-06: Clerk Authentication

Authentication shall be configured and integrated.

**Acceptance Criteria:**
- Clerk application created
- Publishable and secret keys configured in Vercel
- Redirect URLs set to Vercel domain
- Sign-in and sign-up flows functional
- Session management working
- User profile accessible

### FR-07: Secrets Management

All API keys and sensitive configuration shall be securely managed.

**Acceptance Criteria:**
- No secrets committed to repository
- Vercel environment variables configured
- Railway environment variables configured
- .env.example templates provided
- Secrets rotation documented

### FR-08: Monitoring and Observability

Production deployment shall support monitoring and debugging.

**Acceptance Criteria:**
- LangSmith tracing works from deployed backend
- Vercel logs accessible
- Railway logs accessible
- Error tracking functional
- Free tier limits monitored

---

## Pre-Deployment Checklist

Before deploying, verify all components are ready:

### Code Readiness

**Frontend (Next.js):**
```
□ All Next.js code committed to GitHub (askchuck-frontend/)
□ npm run build completes successfully
□ No TypeScript errors
□ package.json dependencies complete
□ .env.example provided with all required variables
□ .gitignore excludes .env.local and node_modules
□ Clerk components integrated
□ Supabase client configured
□ API route for /api/query (SSE proxy) implemented
```

**Backend (FastAPI):**
```
□ All Python code committed to GitHub (ask_chuck_api/)
□ requirements.txt complete with production dependencies
□ FastAPI app starts locally without errors
□ RAG chain initializes successfully
□ /health endpoint responds
□ /stream_query endpoint functional
□ CORS middleware configured
□ .env.example provided
□ .gitignore excludes .env
```

### Data Readiness

```
□ PDF documents processed (PRD-02)
□ Chunks generated with hierarchical structure (PRD-03)
□ Pinecone index populated with ~900 vectors (PRD-04)
□ BM25 encoder fitted and saved (PRD-04)
□ Figures extracted and uploaded to Cloudflare R2 (PRD-02)
□ All R2 URLs verified and accessible
□ Chunk metadata includes r2_url fields
```

### External Services Configuration

**Pinecone:**
```
□ Account created (free tier)
□ Index "askchuck" exists with 1024 dimensions
□ Index populated with parent, child, and figure chunks
□ API key generated
```

**Cloudflare R2:**
```
□ Account created (free tier)
□ Bucket "askchuck" created
□ Figures uploaded (~150 PNG files)
□ Public access enabled
□ CORS policy configured
□ Access Key ID and Secret Access Key generated
```

**Supabase:**
```
□ Project created (free tier)
□ Database tables created (chat_sessions, chat_messages)
□ Row-level security policies applied
□ URL and anon key obtained
```

**Clerk:**
```
□ Application created (free tier - 10K MAU)
□ Publishable key obtained
□ Secret key obtained
□ Redirect URLs configured (will update with Vercel URL)
```

**API Keys:**
```
□ Groq API key valid (free tier)
□ Voyage AI API key valid (free tier - 200M tokens/month)
□ Cohere API key valid (free tier - 1000 calls/month)
□ LangSmith API key valid (free tier - 5K traces/month)
```

### GitHub Repository

```
□ Repository structure organized (frontend/, backend/, .docs/)
□ README.md with setup instructions
□ .gitignore configured for both frontend and backend
□ No secrets in commit history
□ Main branch protection optional (for solo developer)
```

---

## Deployment Steps

### Step 1: Deploy Backend to Railway

Deploy the FastAPI backend first to obtain the backend URL for frontend configuration.

**1.1 Create Railway Project:**

1. Go to https://railway.app/
2. Sign in with GitHub
3. Click "New Project"
4. Select "Deploy from GitHub repo"
5. Choose your AskChuck repository
6. Select the backend directory (ask_chuck_api/)

**1.2 Configure Build Settings:**

- **Root Directory:** `/ask_chuck_api`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`

**1.3 Configure Environment Variables:**

In Railway dashboard, add these environment variables:

```bash
# Groq (LLM and Vision)
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx

# Voyage AI (Embeddings)
VOYAGE_API_KEY=pa-xxxxxxxxxxxxxxxxxxxx

# Pinecone (Vector Database)
PINECONE_API_KEY=pcsk_xxxxxxxxxxxxxxxxxxxx
PINECONE_ENVIRONMENT=us-east-1

# Cohere (Reranking)
COHERE_API_KEY=xxxxxxxxxxxxxxxxxxxx

# Cloudflare R2 (Figure Storage)
CLOUDFLARE_ACCOUNT_ID=xxxxxxxxxxxxxxxxxxxx
CLOUDFLARE_R2_ACCESS_KEY_ID=xxxxxxxxxxxxxxxxxxxx
CLOUDFLARE_R2_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxx
CLOUDFLARE_R2_BUCKET_NAME=askchuck

# LangSmith (Observability)
LANGCHAIN_API_KEY=lsv2_xxxxxxxxxxxxxxxxxxxx
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=askchuck

# Application Settings
PORT=8000
ALLOWED_ORIGINS=https://askchuck.vercel.app
```

**1.4 Deploy and Verify:**

1. Railway will auto-deploy on push to main
2. Check logs for successful startup
3. Note the generated URL: `https://[your-app].up.railway.app`
4. Test health endpoint: `curl https://[your-app].up.railway.app/health`

---

### Step 2: Deploy Frontend to Vercel

Deploy the Next.js frontend with the backend URL from Step 1.

**2.1 Create Vercel Project:**

1. Go to https://vercel.com/
2. Sign in with GitHub
3. Click "Add New Project"
4. Import your AskChuck repository
5. Select the frontend directory (askchuck-frontend/)

**2.2 Configure Build Settings:**

- **Framework Preset:** Next.js
- **Root Directory:** `askchuck-frontend`
- **Build Command:** `npm run build`
- **Output Directory:** `.next`
- **Install Command:** `npm install`

**2.3 Configure Environment Variables:**

In Vercel dashboard, add these environment variables:

**Public Variables (exposed to browser):**
```bash
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxxxxxxxxx
NEXT_PUBLIC_SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xxxx
```

**Private Variables (server-only):**
```bash
CLERK_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxxxxx
BACKEND_API_URL=https://[your-railway-app].up.railway.app
```

**2.4 Deploy and Verify:**

1. Vercel will auto-deploy on push to main
2. Check build logs for successful deployment
3. Note the generated URL: `https://askchuck.vercel.app`
4. Open URL in browser to verify frontend loads

---

### Step 3: Configure Clerk Authentication

Update Clerk with your deployed Vercel URL.

**3.1 Update Redirect URLs:**

1. Go to Clerk Dashboard
2. Navigate to "API Keys"
3. Add authorized redirect URLs:
   - `https://askchuck.vercel.app`
   - `https://askchuck.vercel.app/sign-in`
   - `https://askchuck.vercel.app/sign-up`

**3.2 Configure Sign-In/Sign-Up:**

1. Navigate to "User & Authentication" → "Email, Phone, Username"
2. Enable email authentication
3. Configure sign-in/sign-up options as desired

---

### Step 4: Configure Supabase Database

Set up the database schema and security policies.

**4.1 Create Tables:**

Run this SQL in Supabase SQL Editor:

```sql
-- chat_sessions table
CREATE TABLE chat_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  title TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  message_count INTEGER DEFAULT 0
);

-- chat_messages table
CREATE TABLE chat_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL,
  figures JSONB,
  sources JSONB,
  chunk_ids TEXT[],
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_messages_session_id ON chat_messages(session_id);
CREATE INDEX idx_sessions_updated_at ON chat_sessions(updated_at DESC);
```

**4.2 Enable Row-Level Security:**

```sql
-- Enable RLS
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own sessions
CREATE POLICY "Users can view own sessions"
  ON chat_sessions FOR SELECT
  USING (auth.uid()::text = user_id);

CREATE POLICY "Users can insert own sessions"
  ON chat_sessions FOR INSERT
  WITH CHECK (auth.uid()::text = user_id);

CREATE POLICY "Users can update own sessions"
  ON chat_sessions FOR UPDATE
  USING (auth.uid()::text = user_id);

CREATE POLICY "Users can delete own sessions"
  ON chat_sessions FOR DELETE
  USING (auth.uid()::text = user_id);

-- Policy: Users can only see messages from their sessions
CREATE POLICY "Users can view own messages"
  ON chat_messages FOR SELECT
  USING (
    session_id IN (
      SELECT id FROM chat_sessions WHERE user_id = auth.uid()::text
    )
  );

CREATE POLICY "Users can insert messages to own sessions"
  ON chat_messages FOR INSERT
  WITH CHECK (
    session_id IN (
      SELECT id FROM chat_sessions WHERE user_id = auth.uid()::text
    )
  );
```

---

### Step 5: Configure Cloudflare R2 CORS

Allow Vercel frontend to access figure images.

**5.1 Set CORS Policy:**

In Cloudflare R2 dashboard, navigate to your bucket settings and add CORS policy:

```json
[
  {
    "AllowedOrigins": [
      "https://askchuck.vercel.app"
    ],
    "AllowedMethods": [
      "GET",
      "HEAD"
    ],
    "AllowedHeaders": [
      "*"
    ],
    "ExposeHeaders": [],
    "MaxAgeSeconds": 3600
  }
]
```

**5.2 Verify Public Access:**

Test a figure URL in browser:
```
https://[account-id].r2.cloudflarestorage.com/askchuck/figures/owen_power_of_abstraction_2009_fig_1.png
```

---

### Step 6: Update Railway CORS

Allow Vercel frontend to make API requests to Railway backend.

**6.1 Update Backend CORS:**

Ensure `main.py` includes Vercel domain in CORS origins:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local development
        "https://askchuck.vercel.app"  # Production frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

This should already be configured if following PRD-07 frontend implementation.

---

## Implementation Details

### File: ask_chuck_api/requirements.txt (Production Version)

```python
# FastAPI Framework
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6

# LangChain & LangSmith
langchain==0.1.6
langchain-groq==0.0.3
langsmith==0.0.87

# Vector Database & Embeddings
pinecone-client==3.0.3
voyageai==0.2.1

# Retrieval & Reranking
cohere==4.47

# Storage (Cloudflare R2 - S3 compatible)
boto3==1.34.34

# BM25 Sparse Encoding
pinecone-text==0.7.0

# Utilities
python-dotenv==1.0.0
pydantic==2.5.3
pydantic-settings==2.1.0
tiktoken==0.5.2

# CORS & Security
python-jose[cryptography]==3.3.0

# Notes:
# - PyMuPDF, Pillow excluded (only needed for ingestion, not runtime)
# - docling excluded (only needed for ingestion)
# - ragas excluded (only needed for evaluation)
# - sentence-transformers excluded (using Voyage AI API, not local embeddings)
```

### File: askchuck-frontend/package.json (Production Version)

```json
{
  "name": "askchuck-frontend",
  "version": "2.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "14.1.0",
    "react": "18.2.0",
    "react-dom": "18.2.0",
    "@clerk/nextjs": "^4.29.3",
    "@supabase/supabase-js": "^2.39.3",
    "zustand": "^4.5.0",
    "react-markdown": "^9.0.1",
    "lucide-react": "^0.321.0",
    "tailwindcss": "^3.4.1",
    "autoprefixer": "^10.4.17",
    "postcss": "^8.4.33",
    "@radix-ui/react-avatar": "^1.0.4",
    "@radix-ui/react-dialog": "^1.0.5",
    "@radix-ui/react-dropdown-menu": "^2.0.6",
    "@radix-ui/react-scroll-area": "^1.0.5",
    "@radix-ui/react-separator": "^1.0.3",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.2.1"
  },
  "devDependencies": {
    "typescript": "^5.3.3",
    "@types/node": "^20.11.5",
    "@types/react": "^18.2.48",
    "@types/react-dom": "^18.2.18",
    "eslint": "^8.56.0",
    "eslint-config-next": "14.1.0"
  }
}
```

### File: ask_chuck_api/main.py (Production Entrypoint)

```python
"""
FastAPI backend for AskChuck RAG system.
Exposes /stream_query endpoint for Server-Sent Events streaming.
"""

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.generation.rag_chain import AskChuckRAG
from src.utils.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="AskChuck API",
    description="RAG backend for Charles Owen's Structured Planning literature",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local development
        "https://askchuck.vercel.app"  # Production frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG chain (cached)
rag_chain = None

def get_rag_chain() -> AskChuckRAG:
    """Get or initialize the RAG chain (singleton)."""
    global rag_chain
    if rag_chain is None:
        logger.info("Initializing RAG chain...")
        rag_chain = AskChuckRAG()
        logger.info("RAG chain initialized successfully")
    return rag_chain


@app.on_event("startup")
async def startup_event():
    """Warm up the RAG chain on startup."""
    logger.info("Starting AskChuck API...")
    get_rag_chain()
    logger.info("AskChuck API ready")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "askchuck-api",
        "version": "2.0.0"
    }


class QueryRequest(BaseModel):
    """Request model for query endpoint."""
    question: str
    session_id: str | None = None


@app.post("/query")
async def query(request: QueryRequest):
    """
    Standard (non-streaming) query endpoint.
    Returns complete response after generation finishes.
    """
    try:
        chain = get_rag_chain()
        response = chain.query(
            question=request.question,
            session_id=request.session_id
        )
        return response
    except Exception as e:
        logger.error(f"Query error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stream_query")
async def stream_query(request: QueryRequest):
    """
    Streaming query endpoint using Server-Sent Events.
    Yields tokens, figures, sources, and completion status.
    """
    try:
        chain = get_rag_chain()

        async def event_stream():
            """Generate SSE events from RAG chain."""
            for event in chain.stream_query(
                question=request.question,
                session_id=request.session_id
            ):
                # Format as SSE
                yield f"data: {event}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream"
        )
    except Exception as e:
        logger.error(f"Stream query error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Only for local development
    )
```

### File: askchuck-frontend/.env.example

```bash
# ===========================================
# AskChuck Frontend Environment Variables
# ===========================================
# Copy this to .env.local for local development
# For Vercel deployment, add these in dashboard

# Clerk Authentication (get from clerk.dev dashboard)
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxxxxxxxxx
CLERK_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxxxxx

# Supabase (get from supabase.com dashboard)
NEXT_PUBLIC_SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xxxx

# Backend API (Railway deployment URL)
BACKEND_API_URL=https://[your-railway-app].up.railway.app
```

### File: ask_chuck_api/.env.example

```bash
# ===========================================
# AskChuck Backend Environment Variables
# ===========================================
# Copy this to .env for local development
# For Railway deployment, add these in dashboard

# Groq (LLM and Vision API)
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx

# Voyage AI (Embeddings)
VOYAGE_API_KEY=pa-xxxxxxxxxxxxxxxxxxxx

# Pinecone (Vector Database)
PINECONE_API_KEY=pcsk_xxxxxxxxxxxxxxxxxxxx
PINECONE_ENVIRONMENT=us-east-1

# Cohere (Reranking)
COHERE_API_KEY=xxxxxxxxxxxxxxxxxxxx

# Cloudflare R2 (Figure Storage - S3 compatible)
CLOUDFLARE_ACCOUNT_ID=xxxxxxxxxxxxxxxxxxxx
CLOUDFLARE_R2_ACCESS_KEY_ID=xxxxxxxxxxxxxxxxxxxx
CLOUDFLARE_R2_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxx
CLOUDFLARE_R2_BUCKET_NAME=askchuck

# LangSmith (Observability)
LANGCHAIN_API_KEY=lsv2_xxxxxxxxxxxxxxxxxxxx
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=askchuck

# Application Settings
PORT=8000
ALLOWED_ORIGINS=http://localhost:3000,https://askchuck.vercel.app
```

### File: askchuck-frontend/vercel.json (Optional Configuration)

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "framework": "nextjs",
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "/api/:path*"
    }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        {
          "key": "X-Frame-Options",
          "value": "DENY"
        },
        {
          "key": "X-Content-Type-Options",
          "value": "nosniff"
        }
      ]
    }
  ]
}
```

### File: ask_chuck_api/railway.json (Optional Configuration)

```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn main:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

---

## Post-Deployment Verification

### Verification Checklist

**Frontend (Vercel):**
```
□ https://askchuck.vercel.app is accessible
□ Homepage loads without errors
□ Clerk sign-in flow works (create test account)
□ Clerk sign-up flow works
□ User profile displays correctly
□ Console shows no critical errors
□ Responsive design works on mobile
```

**Backend (Railway):**
```
□ https://[your-app].up.railway.app/health returns 200 OK
□ Railway logs show "RAG chain initialized successfully"
□ No startup errors in Railway dashboard
□ CORS allows requests from Vercel domain
```

**End-to-End Functionality:**
```
□ Can create new chat session
□ Can send a query and receive streaming response
□ Figures display correctly from Cloudflare R2
□ Sources are shown with proper formatting
□ Chunk IDs are accessible in metadata
□ Can view chat history in sidebar
□ Can resume previous chat sessions
□ Can delete chat sessions
□ User data isolated (test with multiple accounts)
```

**Performance:**
```
□ Initial query response starts streaming within 3s
□ Streaming tokens appear in real-time
□ Figure URLs load quickly (<1s)
□ Supabase queries complete quickly (<500ms)
□ No rate limit errors from Groq/Voyage AI/Cohere
```

**Observability:**
```
□ LangSmith traces appear in dashboard
□ Traces include query, retrieval, generation steps
□ Token counts are recorded
□ Latency is recorded for each step
□ Error traces appear if queries fail
```

### Sample Test Queries

Run these queries to verify system functionality:

1. **Basic definition**: "What is a Design Factor?"
   - ✅ Should return definition with sources
   - ✅ Should cite [Context for Creativity, Section X]
   - ✅ Should include Owen terms: Design Factor, Observation, Extension

2. **Visual concept**: "Show me an Information Structure"
   - ✅ Should return description of Information Structures
   - ✅ Should display figure from Cloudflare R2
   - ✅ Should show figure caption

3. **Procedural**: "How do you conduct Action Analysis?"
   - ✅ Should return step-by-step explanation
   - ✅ Should cite multiple sources
   - ✅ Should explain Structured Planning process

4. **Follow-up question**: After query 1, ask "Give me an example"
   - ✅ Should maintain conversation context
   - ✅ Should reference previous discussion
   - ✅ Should retrieve relevant case studies

5. **Out of scope**: "What is Agile methodology?"
   - ✅ Should acknowledge lack of information in Owen's literature
   - ✅ Should not hallucinate information
   - ✅ Should suggest related Structured Planning topics

6. **Session persistence**: Refresh page and check sidebar
   - ✅ Previous chat sessions should appear
   - ✅ Can click on session to resume
   - ✅ Messages load correctly

7. **Multi-user isolation**: Sign in with different account
   - ✅ Should not see other users' chat sessions
   - ✅ Supabase RLS policies enforced

---

## Monitoring and Maintenance

### LangSmith Monitoring

Access LangSmith dashboard at https://smith.langchain.com/ to monitor:

- **Query traces:** Full pipeline visibility (retrieval → generation)
- **Token usage:** Track Groq and Voyage AI consumption
- **Latency:** Identify slow queries or bottlenecks
- **Error rates:** Catch failing queries or API errors
- **User patterns:** Understand common query types

**Key Metrics to Watch:**
- Average query latency (target: < 5s)
- Groq token usage (free tier: 14,400 req/day)
- Voyage AI token usage (free tier: 200M tokens/month)
- Cohere rerank calls (free tier: 1,000/month)
- Error rate (target: < 1%)

### Vercel Analytics

Access Vercel dashboard to monitor:

- **Deployment status:** Track successful/failed builds
- **Function logs:** View API route execution logs
- **Performance metrics:** Core Web Vitals, page load times
- **Error tracking:** Runtime errors in frontend

### Railway Metrics

Access Railway dashboard to monitor:

- **Service health:** Uptime, restart count
- **Resource usage:** RAM, CPU utilization (512MB limit)
- **Deployment logs:** Build and runtime logs
- **Network:** Request count, bandwidth usage

### Usage Limits

Monitor these free tier limits to avoid service interruptions:

| Service | Free Tier Limit | Current Usage | Check Frequency |
|---------|----------------|---------------|-----------------|
| **Groq** | 14,400 requests/day | Check LangSmith | Daily |
| **Voyage AI** | 200M tokens/month | ~540K for indexing + query usage | Weekly |
| **Pinecone** | 2GB storage, unlimited queries | ~10MB (900 vectors) | Monthly |
| **Cohere** | 1,000 calls/month | ~50-100/month (estimated) | Weekly |
| **Cloudflare R2** | 10GB storage, 1M requests/month | ~15MB (150 figures) | Monthly |
| **Supabase** | 500MB storage, unlimited requests | <10MB (chat history) | Monthly |
| **Clerk** | 10,000 MAU | Depends on user adoption | Weekly |
| **Vercel** | 100GB bandwidth/month | Depends on traffic | Weekly |
| **Railway** | $5/month credit | ~$5/month (always-on 512MB) | Weekly |
| **LangSmith** | 5,000 traces/month | ~100-500/month (estimated) | Weekly |

**Alert Thresholds:**
- Set up alerts when approaching 80% of any limit
- Monitor Groq usage daily (14,400 req/day = 600 req/hour)
- Track Cohere reranking carefully (only 1,000/month)

### Updating the Application

**Code Changes:**

1. Make changes locally and test
2. Commit to GitHub:
   ```bash
   git add .
   git commit -m "Description of changes"
   git push origin main
   ```
3. Vercel and Railway auto-deploy from GitHub
4. Monitor deployment logs for success
5. Run post-deployment verification

**Updating Content (Adding New Papers):**

1. Add PDFs to `Charles Owen Papers/` locally
2. Run ingestion pipeline:
   ```bash
   python scripts/ingest_all.py --new-only
   ```
3. Run chunking:
   ```bash
   python scripts/build_chunks.py --new-only
   ```
4. Upload figures to Cloudflare R2:
   ```bash
   python scripts/upload_figures.py
   ```
5. Update Pinecone index:
   ```bash
   python scripts/build_index.py --incremental
   ```
6. No code deployment needed (Pinecone is live)
7. Test new content with queries

**Environment Variable Updates:**

1. For Vercel: Update in Vercel dashboard → Settings → Environment Variables
2. For Railway: Update in Railway dashboard → Variables
3. Redeploy if needed (usually auto-redeploys)

### Rollback Procedure

If a deployment causes issues:

**Option A: Git Revert (Recommended)**
```bash
# Identify problematic commit
git log

# Revert to previous working commit
git revert <commit-hash>
git push origin main

# Vercel and Railway auto-deploy the reverted version
```

**Option B: Vercel Instant Rollback**
1. Go to Vercel dashboard → Deployments
2. Find the last working deployment
3. Click "..." → "Promote to Production"
4. Instant rollback without git changes

**Option C: Railway Rollback**
1. Go to Railway dashboard → Deployments
2. Find the last working deployment
3. Click "Redeploy"

### Debugging Production Issues

**Backend Not Responding:**
1. Check Railway logs for errors
2. Verify environment variables are set
3. Check Pinecone API key is valid
4. Test /health endpoint directly

**Frontend Not Loading:**
1. Check Vercel logs for build errors
2. Verify Clerk keys are configured
3. Check BACKEND_API_URL points to Railway
4. Test in incognito mode (clear cache)

**Figures Not Displaying:**
1. Verify Cloudflare R2 CORS policy
2. Check figure URLs in browser
3. Verify R2 credentials in Railway
4. Check browser console for CORS errors

**Slow Query Performance:**
1. Check LangSmith traces for bottlenecks
2. Verify Pinecone query latency
3. Check Groq API response times
4. Consider caching frequently asked questions

**Authentication Issues:**
1. Verify Clerk redirect URLs match Vercel domain
2. Check Clerk keys are correct
3. Test with different browser
4. Check Supabase RLS policies

---

## Acceptance Criteria

| Criterion | Verification Method | Status |
|-----------|-------------------|--------|
| **Frontend Deployment** | | |
| Vercel build completes successfully | Check Vercel dashboard | □ |
| Frontend URL accessible via HTTPS | Open https://askchuck.vercel.app | □ |
| Next.js pages load without errors | Check browser console | □ |
| Responsive design works | Test on mobile/desktop | □ |
| **Backend Deployment** | | |
| Railway build completes successfully | Check Railway dashboard | □ |
| Backend health endpoint responds | curl https://[app].up.railway.app/health | □ |
| RAG chain initializes | Check Railway logs for success message | □ |
| SSE streaming endpoint works | Test /stream_query | □ |
| **Authentication** | | |
| Clerk sign-in works | Create test account | □ |
| Clerk sign-up works | Create new account | □ |
| User profile displays | Check user dropdown | □ |
| Session management works | Refresh page, verify still logged in | □ |
| **Database** | | |
| Supabase tables exist | Query via SQL editor | □ |
| RLS policies active | Test with multiple accounts | □ |
| Chat sessions persist | Create session, refresh, verify | □ |
| Chat messages persist | Send messages, refresh, verify | □ |
| **RAG Functionality** | | |
| Query returns response | Test "What is a Design Factor?" | □ |
| Streaming works | Observe tokens appearing in real-time | □ |
| Figures display | Query "Show me an Information Structure" | □ |
| Sources shown | Check citation format | □ |
| Chunk IDs accessible | Check metadata/debug view | □ |
| **Performance** | | |
| Query response starts < 3s | Time initial token appearance | □ |
| Full response completes < 10s | Time total query duration | □ |
| Figure URLs load quickly | Check network tab | □ |
| No rate limit errors | Check for API errors | □ |
| **Observability** | | |
| LangSmith traces appear | Check dashboard after query | □ |
| Traces include all steps | Verify retrieval + generation | □ |
| Token counts recorded | Check trace metadata | □ |
| Error tracking works | Trigger error, verify trace | □ |
| **Security** | | |
| No secrets in repository | Search codebase for API keys | □ |
| HTTPS enabled (automatic) | Verify padlock in browser | □ |
| CORS configured correctly | No CORS errors in console | □ |
| RLS enforces user isolation | Test with multiple users | □ |
| **Free Tier Compliance** | | |
| All services within limits | Review usage dashboards | □ |
| No unexpected charges | Check billing for all services | □ |

---

## Production URLs

After deployment, the application will be available at:

**Frontend (User-Facing):**
```
https://askchuck.vercel.app
```

**Backend API (Internal):**
```
https://[your-railway-app].up.railway.app
```

**Service Dashboards:**
- Vercel: https://vercel.com/dashboard
- Railway: https://railway.app/dashboard
- Clerk: https://dashboard.clerk.com/
- Supabase: https://app.supabase.com/
- Pinecone: https://app.pinecone.io/
- Cloudflare: https://dash.cloudflare.com/
- LangSmith: https://smith.langchain.com/

Share the **frontend URL** (askchuck.vercel.app) with users for access to AskChuck.

---

## Next Steps

Once deployment is complete and verified:

1. **User Testing:** Share URL with beta testers (students, researchers)
2. **Feedback Collection:** Gather feedback on response quality and UX
3. **Iteration:** Use LangSmith traces to identify improvement opportunities
4. **Golden Dataset Evaluation:** Run PRD-08 evaluation suite to measure quality
5. **Documentation:** Update README with deployment details and user guide
6. **Optional Enhancements:**
   - Add custom domain (e.g., askchuck.com)
   - Set up staging environment for testing
   - Add analytics (PostHog, Mixpanel)
   - Implement feedback mechanism in UI
   - Create admin dashboard for usage monitoring
