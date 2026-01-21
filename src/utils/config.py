"""
Configuration management for AskChuck.
Loads environment variables and provides typed configuration objects.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

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
    cloudflare_account_id: str = ""
    cloudflare_r2_access_key_id: str = ""
    cloudflare_r2_secret_access_key: str = ""
    cloudflare_r2_bucket_name: str = "askchuck-figures"

    # LangSmith
    langchain_api_key: str = ""
    langchain_tracing_v2: bool = True
    langchain_project: str = "askchuck"
    langchain_endpoint: str = "https://api.smith.langchain.com"

    # Clerk
    clerk_publishable_key: str = ""
    clerk_secret_key: str = ""

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
            max_tokens=5,
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
            top_n=1,
        )
        results["cohere"] = "✓ Connected"
    except Exception as e:
        results["cohere"] = f"✗ Error: {str(e)[:50]}"

    # Test Cloudflare R2 (S3-compatible) - only if credentials are set
    if settings.cloudflare_account_id and settings.cloudflare_r2_access_key_id:
        try:
            import boto3

            s3_client = boto3.client(
                "s3",
                endpoint_url=f"https://{settings.cloudflare_account_id}.r2.cloudflarestorage.com",
                aws_access_key_id=settings.cloudflare_r2_access_key_id,
                aws_secret_access_key=settings.cloudflare_r2_secret_access_key,
            )
            s3_client.list_objects_v2(
                Bucket=settings.cloudflare_r2_bucket_name, MaxKeys=1
            )
            results["cloudflare_r2"] = "✓ Connected"
        except Exception as e:
            results["cloudflare_r2"] = f"✗ Error: {str(e)[:50]}"
    else:
        results["cloudflare_r2"] = "⊘ Not configured (optional for PRD-02+)"

    # Test LangSmith - only if API key is set
    if settings.langchain_api_key:
        try:
            from langsmith import Client

            client = Client(api_key=settings.langchain_api_key)
            list(client.list_projects(limit=1))
            results["langsmith"] = "✓ Connected"
        except Exception as e:
            results["langsmith"] = f"✗ Error: {str(e)[:50]}"
    else:
        results["langsmith"] = "⊘ Not configured (optional, recommended for debugging)"

    return results
