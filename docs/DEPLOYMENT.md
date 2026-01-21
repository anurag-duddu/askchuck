# AskChuck Deployment Guide

**Version:** 2.0
**Last Updated:** 2026-01-20
**Current Stack:** FastAPI + Next.js

> **⚠️ DEPRECATION NOTICE:** Streamlit has been completely removed from this project. This document contains historical references to Streamlit deployment, but all Streamlit code, configuration, and dependencies have been removed. The project now uses Next.js for the frontend.

---

## Overview

This guide covers deploying the AskChuck RAG system with the current Streamlit + FastAPI architecture. Multiple deployment options are provided to suit different needs and infrastructure preferences.

---

## Prerequisites

### Required Services

Before deploying, ensure you have accounts and API keys for:

| Service | Purpose | Free Tier | Sign Up Link |
|---------|---------|-----------|--------------|
| **Groq** | LLM inference (Llama 3.3 70B) | 14,400 req/day | https://console.groq.com/ |
| **Voyage AI** | Text embeddings (voyage-3) | 200M tokens/month | https://www.voyageai.com/ |
| **Pinecone** | Vector database | 2GB storage | https://app.pinecone.io/ |
| **Cohere** | Reranking (rerank-v3.0) | 1,000 calls/month | https://dashboard.cohere.com/ |
| **Cloudflare R2** | Figure storage | 10GB storage | https://dash.cloudflare.com/ |
| **LangSmith** | Observability | 5,000 traces/month | https://smith.langchain.com/ |

### Data Preparation

Ensure the following have been completed:

- ✅ **Documents ingested** (PRD-02): PDFs processed, figures extracted
- ✅ **Chunks created** (PRD-03): Hierarchical chunks with contextual enrichment
- ✅ **Index built** (PRD-04): Pinecone index populated with ~900 vectors
- ✅ **Figures uploaded** (PRD-02): Cloudflare R2 bucket with ~150 PNG files
- ✅ **BM25 encoder trained** (PRD-04): `data/bm25_encoder.pkl` exists

---

## Deployment Options

### Option 1: Docker Compose (Recommended for Local/VPS)

**Best for:** Full control, local development, VPS deployment

**Pros:**
- Complete isolation
- Easy to replicate
- Both FastAPI and Streamlit in one stack
- Health checks and restart policies

**Cons:**
- Requires Docker knowledge
- Manual deployment to production

#### Steps:

1. **Clone repository**
   ```bash
   git clone https://github.com/yourusername/askchuck.git
   cd askchuck
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Build and run**
   ```bash
   docker-compose up --build
   ```

4. **Access services**
   - FastAPI: http://localhost:8000
   - Streamlit: http://localhost:8501
   - API Docs: http://localhost:8000/docs

5. **Production deployment** (on VPS)
   ```bash
   # Use production compose file
   docker-compose -f docker-compose.prod.yml up -d
   ```

---

### Option 2: Railway (Backend) + Local Streamlit

**Best for:** Public API with local UI testing

**Pros:**
- FastAPI always available
- Free tier ($5/month credit)
- Auto-deployment from GitHub
- HTTPS by default

**Cons:**
- Streamlit not publicly accessible
- Requires local Streamlit startup

#### Steps:

1. **Deploy to Railway**

   a. Go to https://railway.app/

   b. Click "New Project" → "Deploy from GitHub repo"

   c. Select askchuck repository

   d. Configure build settings:
   ```
   Build Command: pip install -r requirements.txt
   Start Command: uvicorn src.api.server:app --host 0.0.0.0 --port $PORT
   ```

   e. Add environment variables (copy from .env.example)

   f. Deploy and note the URL: `https://[your-app].up.railway.app`

2. **Test backend**
   ```bash
   curl https://[your-app].up.railway.app/health
   ```

3. **Run Streamlit locally**
   ```bash
   # Update .env with Railway URL if needed
   streamlit run streamlit_app.py
   ```

---

### Option 3: Streamlit Cloud + Railway

**Best for:** Public demo with minimal setup

**Pros:**
- Both services publicly accessible
- No server management
- Free tiers for both

**Cons:**
- Streamlit Cloud can be slow
- Limited customization

#### Steps:

1. **Deploy FastAPI to Railway** (see Option 2, Step 1)

2. **Deploy Streamlit to Streamlit Cloud**

   a. Go to https://share.streamlit.io/

   b. Connect GitHub repository

   c. Select main branch and streamlit_app.py

   d. Add secrets (Environment Variables):
   ```
   # Add all keys from .env.example
   ```

   e. Deploy

3. **Access**
   - API: https://[your-app].up.railway.app
   - Streamlit: https://[your-app].streamlit.app

---

### Option 4: Self-Hosted VPS (DigitalOcean, Hetzner)

**Best for:** Full control, cost-effective for sustained traffic

**Pros:**
- Complete ownership
- Predictable costs
- Better performance

**Cons:**
- Requires server administration
- Manual deployment and updates

#### Steps:

1. **Provision VPS** (Ubuntu 22.04 LTS, 2GB RAM minimum)

2. **Install Docker**
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER
   ```

3. **Install Docker Compose**
   ```bash
   sudo apt-get update
   sudo apt-get install docker-compose-plugin
   ```

4. **Clone and deploy**
   ```bash
   git clone https://github.com/yourusername/askchuck.git
   cd askchuck
   cp .env.example .env
   # Edit .env
   docker-compose up -d
   ```

5. **Set up reverse proxy (nginx)**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://localhost:8501;  # Streamlit
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
       }

       location /api {
           proxy_pass http://localhost:8000;  # FastAPI
       }
   }
   ```

6. **Enable HTTPS with Let's Encrypt**
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

---

## Environment Configuration

### Required Variables

The `.env.example` file provides a template. All variables are required except where noted.

**Critical Variables:**
```bash
GROQ_API_KEY=gsk_...          # Required for LLM inference
VOYAGE_API_KEY=pa-...         # Required for embeddings
PINECONE_API_KEY=pcsk_...     # Required for vector search
COHERE_API_KEY=...            # Required for reranking
CLOUDFLARE_R2_ACCESS_KEY_ID=...  # Required for figures
CLOUDFLARE_R2_SECRET_ACCESS_KEY=...
LANGCHAIN_API_KEY=lsv2_...    # Required for tracing
```

**Optional Variables:**
```bash
CLERK_PUBLISHABLE_KEY=...     # Only for Next.js frontend
CLERK_SECRET_KEY=...          # Only for Next.js frontend
DEBUG=true                    # Set to false in production
```

### Security Best Practices

1. **Never commit .env** - It's in .gitignore, keep it that way
2. **Use different keys** for development and production
3. **Rotate keys** periodically
4. **Limit CORS origins** in production
5. **Enable HTTPS** for all external access

---

## Health Checks and Monitoring

### Health Endpoints

**FastAPI Backend:**
```bash
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "service": "askchuck-api",
  "version": "2.0.0"
}
```

### LangSmith Monitoring

All queries are traced to LangSmith for observability:

1. Go to https://smith.langchain.com/
2. Select "askchuck" project
3. View traces for:
   - Query execution time
   - Retrieval performance
   - Token usage
   - Error rates

### Log Locations

**Docker Compose:**
```bash
docker-compose logs api        # FastAPI logs
docker-compose logs streamlit  # Streamlit logs
docker-compose logs -f         # Follow all logs
```

**Railway:**
- View logs in Railway dashboard
- Real-time log streaming available

---

## Scaling Considerations

### Traffic Thresholds

With free tiers, you can handle approximately:
- **100-500 queries/day** comfortably
- **14,400 queries/day** Groq limit (hard cap)
- **1,000 rerank calls/month** Cohere limit

### When to Upgrade

Consider paid tiers if:
- Groq queries exceed 10,000/day
- Cohere reranking exceeds 800 calls/month
- Pinecone index grows beyond 2GB
- Railway RAM exceeds 512MB consistently

### Optimization Tips

1. **Cache frequently asked questions**
   - Store common Q&A pairs in memory or Redis
   - Bypass RAG for exact matches

2. **Batch reranking**
   - Only rerank when precision is critical
   - Skip reranking for simple definition queries

3. **Reduce top_k**
   - Retrieve fewer chunks (e.g., 3 instead of 5)
   - Reduces reranking calls and LLM context size

---

## Troubleshooting

### Common Issues

**1. FastAPI fails to start**

*Symptom:* Container exits immediately

*Solutions:*
```bash
# Check logs
docker-compose logs api

# Common causes:
# - Missing environment variables → Check .env
# - Pinecone API key invalid → Verify at https://app.pinecone.io/
# - Port 8000 already in use → Change PORT in .env
```

**2. Streamlit can't connect to RAG chain**

*Symptom:* "Error initializing RAG chain"

*Solutions:*
```bash
# Check if all services are reachable
curl http://localhost:8000/health

# Verify environment variables are loaded
docker-compose config

# Restart services
docker-compose restart
```

**3. Figures not displaying**

*Symptom:* Broken image icons

*Solutions:*
```bash
# Verify R2 URLs are public
curl -I https://[account-id].r2.cloudflarestorage.com/askchuck/figures/test.png

# Check CORS configuration in Cloudflare dashboard
# Ensure ALLOWED_ORIGINS includes Streamlit domain
```

**4. Slow query performance**

*Symptom:* Queries take > 10 seconds

*Solutions:*
- Check LangSmith traces for bottlenecks
- Verify Pinecone query latency (should be < 500ms)
- Reduce top_k retrieval
- Check Groq API response times

**5. Rate limit errors**

*Symptom:* HTTP 429 errors

*Solutions:*
- Check Groq daily limit (14,400/day = 600/hour)
- Monitor Cohere reranking calls
- Implement request queuing or throttling

---

## Production Checklist

Before going live:

**Security:**
- [ ] All API keys in environment variables (not hardcoded)
- [ ] `.env` file is gitignored and never committed
- [ ] HTTPS enabled (via Let's Encrypt or platform default)
- [ ] CORS restricted to known domains
- [ ] Debug mode disabled (`DEBUG=false`)

**Performance:**
- [ ] Health checks configured and passing
- [ ] LangSmith tracing operational
- [ ] Query latency < 5 seconds for 95th percentile
- [ ] Free tier limits documented and monitored

**Reliability:**
- [ ] Restart policies configured (Docker/Railway)
- [ ] Error logging and monitoring active
- [ ] Backup of BM25 encoder and chunked data
- [ ] Pinecone index backed up (export vectors)

**Functionality:**
- [ ] Test queries return expected results
- [ ] Figures display correctly
- [ ] Sources are properly cited
- [ ] Streaming works smoothly
- [ ] Multi-turn conversations maintain context

---

## Maintenance

### Regular Tasks

**Daily:**
- Monitor Groq usage (LangSmith dashboard)
- Check error rates

**Weekly:**
- Review LangSmith traces for issues
- Check free tier limits across all services
- Review user feedback (if public)

**Monthly:**
- Rotate API keys
- Update dependencies (`pip list --outdated`)
- Backup Pinecone index
- Review and update golden dataset

### Updating Content

To add new Owen papers:

```bash
# 1. Add PDFs
cp new-paper.pdf "Charles Owen Papers/"

# 2. Ingest
python scripts/ingest_documents.py --new-only

# 3. Chunk
python scripts/chunk_documents.py --new-only

# 4. Upload figures
python scripts/upload_figures.py

# 5. Index
python scripts/build_index.py --incremental

# 6. Verify
curl http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Test question about new content"}'
```

---

## Next Steps: Migrating to Next.js

The current deployment uses Streamlit for the UI. For production-grade deployment with authentication and persistence, migrate to Next.js:

**Reference:** `docs/NEXT_JS_ARCHITECTURE.md`

**Benefits:**
- Clerk authentication
- Supabase chat persistence
- Professional UI/UX
- Better SEO and performance

**Migration Path:**
1. Build Next.js frontend (follow PRD-07 architecture)
2. Deploy to Vercel (free tier)
3. FastAPI backend remains on Railway (reusable)
4. Gradually transition users from Streamlit to Next.js

---

## Support

- **Issues:** https://github.com/yourusername/askchuck/issues
- **Documentation:** `docs/` directory
- **LangSmith:** https://smith.langchain.com/

---

**Deployment Status: Ready for Production**

The current Streamlit + FastAPI stack is production-ready for academic and research use. For commercial deployment with authentication and persistence, follow the Next.js migration guide.
