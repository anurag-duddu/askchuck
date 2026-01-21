# PRD-01: Environment Setup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Set up complete development environment for AskChuck RAG system from scratch

**Architecture:** Python-based RAG system with cloud services (Groq, Voyage AI, Pinecone, Cohere, Cloudflare R2) for zero-cost operation. Modular structure with separate directories for ingestion, chunking, indexing, retrieval, and generation.

**Tech Stack:** Python 3.11+, LangChain, Pinecone, Voyage AI, Groq, Cohere, Cloudflare R2, LangSmith

---

## Task 1: Create Project Directory Structure

**Files:**
- Create: `data/raw/`, `data/processed/`, `data/chunks/`, `data/figures/`
- Create: `src/ingestion/`, `src/chunking/`, `src/indexing/`, `src/retrieval/`, `src/generation/`, `src/utils/`
- Create: `scripts/`, `tests/`

**Step 1: Create data directories**

```bash
mkdir -p data/{raw,processed,chunks,figures}
```

**Step 2: Create source code directories**

```bash
mkdir -p src/{ingestion,chunking,indexing,retrieval,generation,utils}
```

**Step 3: Create supporting directories**

```bash
mkdir -p scripts tests
```

**Step 4: Create __init__.py files**

```bash
touch src/__init__.py
touch src/ingestion/__init__.py
touch src/chunking/__init__.py
touch src/indexing/__init__.py
touch src/retrieval/__init__.py
touch src/generation/__init__.py
touch src/utils/__init__.py
touch tests/__init__.py
```

**Step 5: Verify directory structure**

```bash
tree -L 2 -d
```

Expected output: Nested directory structure with data/, src/, scripts/, tests/

**Step 6: Commit**

```bash
git add data/ src/ scripts/ tests/
git commit -m "feat: create project directory structure

- Add data directories for raw PDFs, processed files, chunks, and figures
- Add src directories for modular RAG pipeline components
- Add scripts and tests directories
- Initialize all Python packages with __init__.py

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Create Requirements File

**Files:**
- Create: `requirements.txt`

**Step 1: Create requirements.txt with pinned versions**

```bash
cat > requirements.txt << 'EOF'
# Core Framework
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

# Document Processing
pymupdf==1.23.21
pillow==10.2.0

# Storage
boto3==1.34.34

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
EOF
```

**Step 2: Verify file creation**

```bash
cat requirements.txt
```

Expected: File contains all dependencies with pinned versions

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "feat: add requirements.txt with pinned dependencies

- LangChain ecosystem for RAG pipeline
- Pinecone for vector storage
- Voyage AI for embeddings
- Cohere for reranking
- PyMuPDF for PDF processing
- Development and evaluation tools

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Create Environment Configuration Files

**Files:**
- Create: `.env.example`
- Modify: `.env` (user must add their own API keys)

**Step 1: Create .env.example template**

```bash
cat > .env.example << 'EOF'
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
EOF
```

**Step 2: Verify .env.example**

```bash
cat .env.example
```

Expected: Template file with all required environment variables

**Step 3: Update existing .env with new structure**

```bash
# User must manually update their .env file with actual API keys
# For now, just create a backup
cp .env .env.backup
```

**Step 4: Commit**

```bash
git add .env.example
git commit -m "feat: add environment configuration template

- Template for all required API keys
- Links to service registration pages
- Development defaults for non-secret values

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Create Configuration Management Module

**Files:**
- Create: `src/utils/config.py`

**Step 1: Create config.py with Settings class**

```python
cat > src/utils/config.py << 'EOF'
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
EOF
```

**Step 2: Verify config.py**

```bash
cat src/utils/config.py | head -20
```

Expected: File starts with docstring and imports

**Step 3: Commit**

```bash
git add src/utils/config.py
git commit -m "feat: add configuration management module

- Pydantic Settings for typed environment variables
- Project path constants
- API connection verification functions
- Global settings instance

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Create Verification Script

**Files:**
- Create: `scripts/verify_setup.py`

**Step 1: Create verify_setup.py**

```python
cat > scripts/verify_setup.py << 'EOF'
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
EOF
```

**Step 2: Make script executable**

```bash
chmod +x scripts/verify_setup.py
```

**Step 3: Verify script creation**

```bash
cat scripts/verify_setup.py | head -15
```

Expected: Script starts with docstring and imports

**Step 4: Commit**

```bash
git add scripts/verify_setup.py
git commit -m "feat: add environment verification script

- Checks directory structure
- Verifies environment variables are set
- Tests all API connections
- Reports status with clear visual indicators

Usage: python scripts/verify_setup.py

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Install Dependencies and Test

**Files:**
- None (testing only)

**Step 1: Check if virtual environment exists**

```bash
ls -la | grep venv || echo "No venv found"
```

**Step 2: Create virtual environment if needed**

```bash
python3 -m venv venv
```

**Step 3: Activate virtual environment**

```bash
source venv/bin/activate
```

**Step 4: Upgrade pip**

```bash
pip install --upgrade pip
```

**Step 5: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: All packages install successfully without errors

**Step 6: Verify installation**

```bash
pip list | grep -E "(langchain|pinecone|voyage|cohere|pymupdf)"
```

Expected: All key packages shown with correct versions

**Step 7: Run verification script (will fail without API keys)**

```bash
python scripts/verify_setup.py
```

Expected: Script runs, shows missing environment variables (unless user has already set them up)

---

## Task 7: Documentation and Next Steps

**Files:**
- Create: `docs/SETUP_COMPLETE.md`

**Step 1: Create completion checklist**

```bash
cat > docs/SETUP_COMPLETE.md << 'EOF'
# PRD-01 Environment Setup - Completion Checklist

## ✅ Completed Steps

- [x] Project directory structure created
- [x] requirements.txt created with pinned versions
- [x] .env.example template created
- [x] Configuration management module created
- [x] Verification script created
- [x] Virtual environment created
- [x] Dependencies installed

## ⏭️ Next Steps for User

### 1. Obtain API Keys

Visit these services and create accounts:

1. **Groq**: https://console.groq.com/ → Create API Key
2. **Voyage AI**: https://www.voyageai.com/ → Dashboard → API Keys
3. **Pinecone**: https://www.pinecone.io/ → Sign up → API Keys
4. **Cohere**: https://dashboard.cohere.com/ → Sign up → API Keys
5. **Cloudflare R2**: https://dash.cloudflare.com/ → R2 → Create Bucket → API Token
6. **LangSmith**: https://smith.langchain.com/ → Settings → API Keys
7. **Clerk**: https://clerk.com/ → Create Application → API Keys

### 2. Configure .env File

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
# Edit .env with your actual API keys
```

### 3. Add PDF Files

Place Charles Owen's papers in `data/raw/`:

```bash
# Copy PDFs from "Charles Owen Papers/" to data/raw/
cp "Charles Owen Papers/"*.pdf data/raw/
```

### 4. Verify Setup

Run the verification script:

```bash
python scripts/verify_setup.py
```

All checks should pass (✓).

### 5. Proceed to PRD-02

Once verification passes, proceed to **PRD-02: Document Ingestion** to begin processing PDFs.

## 📚 References

- PRD-01: `.docs/PRD-01-Environment-Setup.md`
- Configuration: `src/utils/config.py`
- Verification: `scripts/verify_setup.py`
EOF
```

**Step 2: Verify documentation**

```bash
cat docs/SETUP_COMPLETE.md
```

**Step 3: Commit**

```bash
git add docs/SETUP_COMPLETE.md
git commit -m "docs: add setup completion checklist

- Document completed steps
- Provide clear next steps for user
- Link to external service registration
- Guide for API key configuration

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

**Step 4: Final git status check**

```bash
git status
```

Expected: Working tree clean (all changes committed)

**Step 5: Show directory tree**

```bash
tree -L 3 -I 'venv|__pycache__|*.pyc'
```

Expected: Complete project structure visible

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| ✅ All directories created | `tree -d` shows data/, src/, scripts/, tests/ |
| ✅ requirements.txt exists with pinned versions | `cat requirements.txt` shows all dependencies |
| ✅ .env.example template created | `cat .env.example` shows all required vars |
| ✅ Configuration module created | `cat src/utils/config.py` shows Settings class |
| ✅ Verification script created | `scripts/verify_setup.py` runs without errors |
| ✅ Virtual environment created | `which python` shows venv/bin/python |
| ✅ Dependencies installed | `pip list` shows all packages |
| ✅ All changes committed | `git status` shows clean working tree |

## User Action Required

After this plan completes, the **user must**:

1. **Obtain API keys** from all 7 services (see docs/SETUP_COMPLETE.md)
2. **Update .env** with their actual API keys
3. **Copy PDFs** to `data/raw/` directory
4. **Run verification**: `python scripts/verify_setup.py`

Once verification passes, environment setup is complete and the system is ready for PRD-02 (Document Ingestion).

---

## Notes

- Python 3.13.0 detected (meets 3.11+ requirement)
- Legacy `ask_chuck_api/` directory removed
- `.gitignore` updated to track new project structure
- All secret files properly excluded from git
- PRD documents remain unchanged in `.docs/`
