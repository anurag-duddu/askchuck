# PRD-01: Environment Setup

## Document Information

| Field | Value |
|-------|-------|
| PRD ID | PRD-01 |
| Version | 2.0 |
| Phase | 0 |
| Estimated Duration | 30 minutes |
| Dependencies | None |
| Owner | Developer |
| Last Updated | January 2026 |

---

## Objective

Establish the complete development environment for AskChuck, including all external service accounts, API credentials, Python environment, and project directory structure. Upon completion, all API connections should be verified and the project scaffold ready for implementation.

**Key Changes from v1.0:**
- Switched from HuggingFace/BGE to Voyage AI for embeddings
- Switched from Supabase to Cloudflare R2 for file storage
- Switched from Google OAuth to Clerk for authentication
- Added Pinecone for vector database with native hybrid search
- **PDF extraction finalized:** PyMuPDF with page rendering for vector graphics

---

## Required External Accounts

Create accounts and obtain API keys from the following services in this order:

### 1. Groq (Primary LLM Provider)

**Purpose:** Text generation (Llama 3.3 70B), contextual enrichment, query expansion, and image understanding (Llama 3.2 Vision)

**Account Setup:**
1. Navigate to https://console.groq.com/
2. Sign up with Google or email
3. Verify email if required
4. Navigate to Console → API Keys → Create API Key
5. Name it "askchuck-dev"
6. Copy and save the key immediately (shown only once)

**Free Tier Limits:**
- llama-3.3-70b-versatile: 30 RPM, 1K RPD, 12K TPM, 100K TPD
- llama-3.1-8b-instant: 30 RPM, 14.4K RPD, 6K TPM, 500K TPD
- llama-3.2-90b-vision-preview: Vision model for figure descriptions

**Environment Variable:**
```
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

### 2. Voyage AI (Embeddings)

**Purpose:** Best-in-class embedding generation for RAG retrieval

**Account Setup:**
1. Navigate to https://www.voyageai.com/
2. Sign up with email or Google
3. Navigate to Dashboard → API Keys
4. Create new API key
5. Copy the key

**Free Tier Limits:**
- 200M tokens/month
- Access to voyage-3 model (1024 dimensions)
- Rate limit: 300 RPM

**Why Voyage AI?**
- Ranked #1 on MTEB for RAG retrieval tasks
- Optimized for passage-level retrieval (not just sentence similarity)
- Handles technical/academic vocabulary well
- Model diversity from Cohere reranker (reduces correlated errors)

**Environment Variable:**
```
VOYAGE_API_KEY=pa-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

### 3. Pinecone (Vector Database)

**Purpose:** Vector storage with native hybrid search (dense + sparse vectors)

**Account Setup:**
1. Navigate to https://www.pinecone.io/
2. Sign up with Google or email
3. Select "Serverless" plan (free tier)
4. Create new project if prompted
5. Navigate to API Keys
6. Copy the API key
7. Note your environment/region (e.g., "us-east-1")

**Free Tier Limits:**
- 2GB storage
- Unlimited queries
- Native hybrid search included
- 1 serverless index

**Why Pinecone?**
- Native hybrid search (dense + sparse vectors in single index)
- Eliminates need for separate BM25 index and manual RRF fusion
- Unlimited queries on free tier (vs usage-based pricing)
- Production-proven vector database

**Environment Variables:**
```
PINECONE_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
PINECONE_ENVIRONMENT=us-east-1
```

---

### 4. Cohere (Reranking)

**Purpose:** Cross-encoder reranking of retrieved documents

**Account Setup:**
1. Navigate to https://dashboard.cohere.com/welcome/register
2. Sign up with Google or email
3. Complete onboarding questionnaire (select "Personal Project")
4. Navigate to Dashboard → API Keys
5. Copy the Trial API key

**Free Tier Limits:**
- 1,000 API calls/month
- Access to rerank-v3.0 model
- Rate limit: 10 calls/minute

**Why Cohere rerank-v3.0?**
- Best-in-class cross-encoder for relevance scoring
- Model diversity from Voyage AI embeddings (different architecture and training data)
- Precise relevance scoring after initial retrieval

**Environment Variable:**
```
COHERE_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

### 5. Cloudflare R2 (File Storage)

**Purpose:** Store PDFs and extracted figure images, serve via public URLs

**Account Setup:**
1. Navigate to https://dash.cloudflare.com/
2. Sign up or log in with email
3. Navigate to R2 Object Storage
4. Click "Create bucket"
   - Name: "askchuck-figures"
   - Region: Automatic
5. After creation, navigate to Settings → API Tokens
6. Create API Token:
   - Token name: "askchuck-r2-access"
   - Permissions: Object Read & Write
   - Copy Access Key ID and Secret Access Key
7. Note your Account ID (in dashboard URL or Settings)

**Free Tier Limits:**
- 10GB storage
- 1M Class A operations/month (writes)
- 10M Class B operations/month (reads)
- Free egress (unlike S3)

**Why Cloudflare R2?**
- S3-compatible API (easy integration)
- Free egress bandwidth (S3 charges for downloads)
- Generous free tier for 20 papers + figures
- Production-grade reliability

**Environment Variables:**
```
CLOUDFLARE_ACCOUNT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
CLOUDFLARE_R2_ACCESS_KEY_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
CLOUDFLARE_R2_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
CLOUDFLARE_R2_BUCKET_NAME=askchuck-figures
```

---

### 6. LangSmith (Observability)

**Purpose:** Tracing, debugging, and evaluation of RAG pipeline

**Account Setup:**
1. Navigate to https://smith.langchain.com/
2. Sign up with Google or GitHub
3. Create a new organization if prompted
4. Navigate to Settings → API Keys → Create API Key
5. Copy the key

**Free Tier Limits:**
- 5,000 traces/month
- 14-day data retention
- Basic evaluation features

**Environment Variables:**
```
LANGCHAIN_API_KEY=lsv2_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=askchuck
```

---

### 7. Clerk (Authentication)

**Purpose:** User authentication for the deployed application

**Account Setup:**
1. Navigate to https://clerk.com/
2. Sign up with email or Google
3. Create new application:
   - Name: "AskChuck"
   - Authentication: Email + Google Social Login
4. Navigate to API Keys
5. Copy "Publishable Key" and "Secret Key"

**Free Tier Limits:**
- 10,000 monthly active users
- Unlimited applications
- Email + Social auth included

**Important: Custom Domain Required**
- Clerk does NOT work on free hosting subdomains (e.g., free Vercel deployments)
- You must have a custom domain (e.g., askchuck.yourdomain.com)
- Set up custom domain BEFORE configuring Clerk in production

**Environment Variables:**
```
CLERK_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
CLERK_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

### 8. GitHub (Code Repository)

**Purpose:** Version control and deployment source

**Account Setup:**
1. If not already registered, create account at https://github.com
2. Create new repository:
   - Name: "askchuck"
   - Visibility: Private (or Public if desired)
   - Initialize with README: No
   - .gitignore: Python
   - License: MIT (optional)
3. Note the repository URL

**No API key required for basic usage**

---

## Python Environment Setup

### System Requirements

- Python 3.11 or higher
- pip (latest version)
- Git
- 4GB RAM minimum (no local embedding model needed)
- 3GB disk space (for PDFs, figures, and dependencies)

### Virtual Environment Creation

```bash
# Create project directory
mkdir askchuck
cd askchuck

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
.\venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip
```

### Dependencies (requirements.txt)

Create `requirements.txt` with **version pinning** for reproducibility:

```
# Core Framework (TBD in PRD-07 - may replace Streamlit)
streamlit==1.29.0

# LangChain Ecosystem
langchain==0.1.10
langchain-community==0.0.24
langchain-groq==0.0.3
langchain-text-splitters==0.0.1
langsmith==0.0.87

# Vector Store
pinecone-client==3.0.3

# Embeddings
voyageai==0.2.1

# Retrieval & Reranking
cohere==4.47

# Document Processing (finalized after evaluation)
pymupdf==1.23.21  # PDF parsing and page rendering for vector graphics
pillow==10.2.0    # Image processing

# Storage
boto3==1.34.34  # For Cloudflare R2 (S3-compatible)

# Utilities
python-dotenv==1.0.0
pydantic==2.5.3
pydantic-settings==2.1.0
tqdm==4.66.1
pandas==2.2.0

# Evaluation
ragas==0.1.5
datasets==2.16.1

# Development
pytest==7.4.4
black==24.1.1
isort==5.13.2
```

**Note:** Version numbers reflect latest stable releases as of January 2026. Update as needed while maintaining compatibility.

### Install Dependencies

```bash
pip install -r requirements.txt
```

**No model downloads required** - Voyage AI is API-based, not local inference.

---

## PDF Figure Extraction: Finalized Approach

**Evaluation completed January 2026** - See [.docs/PDF-EXTRACTION-EVALUATION-FINDINGS.md](.docs/PDF-EXTRACTION-EVALUATION-FINDINGS.md) for detailed analysis.

### Key Finding: Vector Graphics in Academic PDFs

Owen's papers contain **vector graphics** (PDF drawing commands), not embedded raster images. Traditional `get_images()` extraction fails, extracting only 2 figures from 4 test papers despite 33+ figure references.

**Root cause:** Figures are drawn with PDF vector commands (paths, strokes, fills), not embedded as JPEG/PNG images.

### Solution: Page Region Rendering

**Use PyMuPDF to render page regions as high-resolution images at 300 DPI.**

```python
# Identify figure location via caption detection
figure_bbox = find_figure_bounding_box(page, caption)

# Render that region at 300 DPI
zoom = 300 / 72  # Convert to DPI scale
mat = fitz.Matrix(zoom, zoom)
pix = page.get_pixmap(matrix=mat, clip=figure_bbox)
pix.save("figure.png")
```

### Evaluation Results

**Tested on 4 representative papers (32 pages total):**

| Metric | Result |
|--------|--------|
| Figures extracted (traditional method) | 2 / 33+ |
| Figures extracted (page rendering) | 10 / 10 tested |
| Output quality | Excellent (1,561-1,985px wide) |
| File sizes | 95-173KB per figure |
| Caption detection success | 3 / 4 papers |
| Vector graphics handled | ✅ Yes |

**Visual verification:** Extracted figures are crisp, clear, with readable text and diagrams suitable for Groq Vision processing.

### Why This Approach Works

✅ **Handles all figure types:**
- Vector graphics (primary type in Owen's papers)
- Embedded raster images
- Tables and matrices
- Mixed content

✅ **High quality:** Vector graphics render perfectly at any DPI

✅ **No fallbacks needed:** Single unified approach, no quality cascades required

✅ **Simple implementation:** No heavy dependencies beyond PyMuPDF

### Implementation Details

**Caption detection:**
- Regex pattern: `Figure\s+\d+[.\s:]` (case-insensitive)
- Success rate: 75% of test papers
- Fallback: Proximity-based detection for non-standard formats

**Bounding box estimation:**
- Start with heuristic: 250px above caption, full column width
- Refine during implementation using layout analysis
- Acceptable to render larger area and crop afterward

**DPI selection:**
- 300 DPI baseline (excellent quality)
- Increase to 600 DPI for small figures with fine details if needed

**Text extraction:**
- PyMuPDF block-level extraction with (y, x) position sorting
- Alternative: Use Docling if column handling becomes complex
- Decision deferred to PRD-02 implementation phase

### No Fallback Strategies Required

Unlike the initial PRD assumptions, **no fallback cascade is needed** because:
- Page rendering works for ALL figure types uniformly
- Vector graphics have no resolution limitations
- 300 DPI provides excellent quality for all test cases
- No low-quality figures encountered in evaluation

---

## Environment Configuration

### Create .env File

Create `.env` in the project root:

```bash
# ===========================================
# AskChuck Environment Configuration
# ===========================================

# Groq API (LLM and Vision)
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Voyage AI (Embeddings)
VOYAGE_API_KEY=pa-xxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Pinecone (Vector Database)
PINECONE_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
PINECONE_ENVIRONMENT=us-east-1

# Cohere (Reranking)
COHERE_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Cloudflare R2 (File Storage)
CLOUDFLARE_ACCOUNT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
CLOUDFLARE_R2_ACCESS_KEY_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
CLOUDFLARE_R2_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
CLOUDFLARE_R2_BUCKET_NAME=askchuck-figures

# LangSmith (Observability)
LANGCHAIN_API_KEY=lsv2_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=askchuck
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com

# Clerk (Authentication)
CLERK_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
CLERK_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Application Settings
APP_ENV=development
DEBUG=true
```

### Create .env.example

Create `.env.example` as a template (without actual values):

```bash
# ===========================================
# AskChuck Environment Configuration Template
# ===========================================
# Copy this file to .env and fill in your values

# Groq API - https://console.groq.com/
GROQ_API_KEY=

# Voyage AI - https://www.voyageai.com/
VOYAGE_API_KEY=

# Pinecone - https://www.pinecone.io/
PINECONE_API_KEY=
PINECONE_ENVIRONMENT=

# Cohere - https://dashboard.cohere.com/
COHERE_API_KEY=

# Cloudflare R2 - https://dash.cloudflare.com/
CLOUDFLARE_ACCOUNT_ID=
CLOUDFLARE_R2_ACCESS_KEY_ID=
CLOUDFLARE_R2_SECRET_ACCESS_KEY=
CLOUDFLARE_R2_BUCKET_NAME=askchuck-figures

# LangSmith - https://smith.langchain.com/
LANGCHAIN_API_KEY=
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=askchuck
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com

# Clerk - https://clerk.com/
# NOTE: Requires custom domain in production
CLERK_PUBLISHABLE_KEY=
CLERK_SECRET_KEY=

# Application Settings
APP_ENV=development
DEBUG=true
```

### Create .gitignore

```
# Environment
.env
.env.local
venv/
.venv/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
dist/
*.egg-info/

# Data (large files)
data/raw/*.pdf
data/figures/*.png
data/figures/*.jpg
data/figures_test/
*.pkl

# IDE
.idea/
.vscode/
*.swp
*.swo

# Streamlit (if used)
.streamlit/secrets.toml

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Testing
.coverage
htmlcov/
.pytest_cache/
```

---

## Project Directory Structure

Create the following directory structure:

```bash
# Create all directories
mkdir -p data/{raw,processed,chunks,figures}
mkdir -p src/{ingestion,chunking,indexing,retrieval,generation,utils}
mkdir -p scripts
mkdir -p tests

# Create __init__.py files
touch src/__init__.py
touch src/ingestion/__init__.py
touch src/chunking/__init__.py
touch src/indexing/__init__.py
touch src/retrieval/__init__.py
touch src/generation/__init__.py
touch src/utils/__init__.py
touch tests/__init__.py
```

**Note:** Removed `data/chroma_db/` directory (Pinecone is cloud-hosted, no local storage needed).

---

## Configuration Management

### Create src/utils/config.py

```python
"""
Configuration management for AskChuck.
Loads environment variables and provides typed configuration objects.
"""

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
CHUNKS_DIR = DATA_DIR / "chunks"
FIGURES_DIR = DATA_DIR / "figures"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Groq
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"
    groq_vision_model: str = "llama-3.2-90b-vision-preview"

    # Voyage AI
    voyage_api_key: str
    voyage_model: str = "voyage-3"

    # Pinecone
    pinecone_api_key: str
    pinecone_environment: str
    pinecone_index_name: str = "askchuck"

    # Cohere
    cohere_api_key: str
    cohere_rerank_model: str = "rerank-v3.0"

    # Cloudflare R2
    cloudflare_account_id: str
    cloudflare_r2_access_key_id: str
    cloudflare_r2_secret_access_key: str
    cloudflare_r2_bucket_name: str = "askchuck-figures"

    # LangSmith
    langchain_api_key: str
    langchain_tracing_v2: bool = True
    langchain_project: str = "askchuck"
    langchain_endpoint: str = "https://api.smith.langchain.com"

    # Clerk
    clerk_publishable_key: str
    clerk_secret_key: str

    # Application
    app_env: str = "development"
    debug: bool = True

    # RAG Configuration (defaults, tunable in PRD-05)
    retrieval_top_k: int = 50
    rerank_top_k: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def verify_api_connections() -> dict:
    """
    Verify all API connections are working.
    Returns a dict with service names and their status.
    """
    results = {}

    # Test Groq
    try:
        from groq import Groq
        client = Groq(api_key=settings.groq_api_key)
        client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5
        )
        results["groq"] = "✓ Connected"
    except Exception as e:
        results["groq"] = f"✗ Error: {str(e)[:50]}"

    # Test Voyage AI
    try:
        import voyageai
        client = voyageai.Client(api_key=settings.voyage_api_key)
        client.embed(["test"], model=settings.voyage_model)
        results["voyage"] = "✓ Connected"
    except Exception as e:
        results["voyage"] = f"✗ Error: {str(e)[:50]}"

    # Test Pinecone
    try:
        from pinecone import Pinecone
        pc = Pinecone(api_key=settings.pinecone_api_key)
        pc.list_indexes()
        results["pinecone"] = "✓ Connected"
    except Exception as e:
        results["pinecone"] = f"✗ Error: {str(e)[:50]}"

    # Test Cohere
    try:
        import cohere
        client = cohere.Client(settings.cohere_api_key)
        client.rerank(
            model=settings.cohere_rerank_model,
            query="test",
            documents=["test document"],
            top_n=1
        )
        results["cohere"] = "✓ Connected"
    except Exception as e:
        results["cohere"] = f"✗ Error: {str(e)[:50]}"

    # Test Cloudflare R2 (S3-compatible)
    try:
        import boto3
        s3_client = boto3.client(
            's3',
            endpoint_url=f'https://{settings.cloudflare_account_id}.r2.cloudflarestorage.com',
            aws_access_key_id=settings.cloudflare_r2_access_key_id,
            aws_secret_access_key=settings.cloudflare_r2_secret_access_key
        )
        s3_client.list_objects_v2(Bucket=settings.cloudflare_r2_bucket_name, MaxKeys=1)
        results["cloudflare_r2"] = "✓ Connected"
    except Exception as e:
        results["cloudflare_r2"] = f"✗ Error: {str(e)[:50]}"

    # Test LangSmith
    try:
        from langsmith import Client
        client = Client(api_key=settings.langchain_api_key)
        list(client.list_projects(limit=1))
        results["langsmith"] = "✓ Connected"
    except Exception as e:
        results["langsmith"] = f"✗ Error: {str(e)[:50]}"

    return results
```

---

## Verification Script

### Create scripts/verify_setup.py

```python
"""
Verify that all environment setup is complete and working.
Run this after setting up .env to confirm everything is configured correctly.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import settings, verify_api_connections, PROJECT_ROOT, DATA_DIR


def main():
    print("=" * 60)
    print("AskChuck Environment Verification")
    print("=" * 60)
    print()

    # Check directory structure
    print("📁 Directory Structure:")
    directories = [
        DATA_DIR / "raw",
        DATA_DIR / "processed",
        DATA_DIR / "chunks",
        DATA_DIR / "figures",
    ]
    for d in directories:
        status = "✓" if d.exists() else "✗"
        print(f"   {status} {d.relative_to(PROJECT_ROOT)}")
    print()

    # Check PDF files
    print("📄 PDF Files:")
    pdf_files = list((DATA_DIR / "raw").glob("*.pdf"))
    print(f"   Found {len(pdf_files)} PDF files in data/raw/")
    if pdf_files:
        for pdf in pdf_files[:5]:
            print(f"   - {pdf.name}")
        if len(pdf_files) > 5:
            print(f"   ... and {len(pdf_files) - 5} more")
    print()

    # Check environment variables
    print("🔑 Environment Variables:")
    env_vars = [
        ("GROQ_API_KEY", bool(settings.groq_api_key)),
        ("VOYAGE_API_KEY", bool(settings.voyage_api_key)),
        ("PINECONE_API_KEY", bool(settings.pinecone_api_key)),
        ("COHERE_API_KEY", bool(settings.cohere_api_key)),
        ("CLOUDFLARE_R2_ACCESS_KEY_ID", bool(settings.cloudflare_r2_access_key_id)),
        ("LANGCHAIN_API_KEY", bool(settings.langchain_api_key)),
        ("CLERK_PUBLISHABLE_KEY", bool(settings.clerk_publishable_key)),
    ]
    for name, is_set in env_vars:
        status = "✓" if is_set else "✗"
        print(f"   {status} {name}")
    print()

    # Test API connections
    print("🔌 API Connections:")
    results = verify_api_connections()
    for service, status in results.items():
        print(f"   {status.split()[0]} {service}: {' '.join(status.split()[1:])}")
    print()

    # Summary
    all_passed = all("✓" in str(v) for v in results.values())
    if all_passed:
        print("=" * 60)
        print("✅ All checks passed! Environment is ready.")
        print("=" * 60)
    else:
        print("=" * 60)
        print("⚠️  Some checks failed. Please review the errors above.")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

---

## Acceptance Criteria

| Criterion | Verification Method |
|-----------|-------------------|
| All 8 external accounts created | Manual verification |
| All API keys obtained and saved to .env | Run verify_setup.py |
| Python 3.11+ virtual environment active | `python --version` |
| All dependencies installed with pinned versions | `pip list` shows exact versions |
| Directory structure created | `ls -la` verification |
| Groq API connection works | verify_setup.py passes |
| Voyage AI API connection works | verify_setup.py passes |
| Pinecone connection works | verify_setup.py passes |
| Cohere API connection works | verify_setup.py passes |
| Cloudflare R2 connection works | verify_setup.py passes |
| LangSmith connection works | verify_setup.py passes |
| PDF files placed in data/raw/ | verify_setup.py reports count |
| ✅ PDF extraction evaluation completed | PyMuPDF page rendering approach validated |

---

## Troubleshooting

### Common Issues

**Issue: `ModuleNotFoundError` for any package**
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
pip install -r requirements.txt
```

**Issue: Groq API returns 401 Unauthorized**
- Verify API key is copied correctly (no extra spaces)
- Check if key has been revoked in Groq console
- Create a new API key if needed

**Issue: Voyage AI returns "Invalid API key"**
- Ensure API key starts with "pa-"
- Check for typos in the key
- Verify account has free tier access

**Issue: Pinecone "Index not found"**
- Index will be created in PRD-04 during indexing phase
- For now, just verify API key works with `pc.list_indexes()`

**Issue: Cohere returns "Invalid API key"**
- Ensure you're using the Trial API key, not a production key
- Check for typos in the key

**Issue: Cloudflare R2 "Access Denied"**
- Verify Account ID, Access Key ID, and Secret Access Key match
- Ensure bucket name is correct (case-sensitive)
- Check API token has Read & Write permissions

**Issue: Clerk returns 401**
- Verify you're using the correct key for your environment (test vs production)
- Remember: Clerk requires custom domain in production

**Issue: LangSmith returns 403**
- Verify API key is for the correct organization
- Ensure LANGCHAIN_PROJECT name is valid (alphanumeric, hyphens only)

---

## Next Steps

Once all acceptance criteria are met, proceed to **PRD-02: Document Ingestion** to begin processing the PDF corpus.

**✅ PDF extraction approach finalized:**
- Use PyMuPDF page rendering at 300 DPI for figure extraction
- Evaluation results documented in [.docs/PDF-EXTRACTION-EVALUATION-FINDINGS.md](.docs/PDF-EXTRACTION-EVALUATION-FINDINGS.md)
- PRD-02 updated with page rendering implementation details
