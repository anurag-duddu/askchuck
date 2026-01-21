"""
Verify that all environment setup is complete and working.
Run this after setting up .env to confirm everything is configured correctly.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import (DATA_DIR, PROJECT_ROOT, settings,
                              verify_api_connections)


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
        (
            "CLOUDFLARE_R2_ACCESS_KEY_ID",
            bool(settings.cloudflare_r2_access_key_id),
        ),
        ("LANGCHAIN_API_KEY", bool(settings.langchain_api_key)),
        ("CLERK_PUBLISHABLE_KEY", bool(settings.clerk_publishable_key)),
    ]
    for name, is_set in env_vars:
        status = "✓" if is_set else "⊘"
        note = (
            ""
            if is_set
            else (
                " (optional)"
                if name
                in [
                    "LANGCHAIN_API_KEY",
                    "CLERK_PUBLISHABLE_KEY",
                    "CLOUDFLARE_R2_ACCESS_KEY_ID",
                ]
                else " (missing)"
            )
        )
        print(f"   {status} {name}{note}")
    print()

    # Test API connections
    print("🔌 API Connections:")
    results = verify_api_connections()
    for service, status in results.items():
        print(f"   {status.split()[0]} {service}: {' '.join(status.split()[1:])}")
    print()

    # Summary
    core_services = ["groq", "voyage", "pinecone", "cohere"]
    core_passed = all("✓" in str(results.get(svc, "")) for svc in core_services)

    if core_passed:
        print("=" * 60)
        print("✅ Core services connected! Environment is ready.")
        print("=" * 60)

        # Check optional services
        optional_services = ["cloudflare_r2", "langsmith"]
        optional_missing = [
            svc for svc in optional_services if "⊘" in str(results.get(svc, ""))
        ]
        if optional_missing:
            print()
            print("ℹ️  Optional services not configured:")
            for svc in optional_missing:
                if svc == "cloudflare_r2":
                    print("   - Cloudflare R2 (needed for PRD-02: figure storage)")
                elif svc == "langsmith":
                    print("   - LangSmith (recommended for debugging)")
    else:
        print("=" * 60)
        print("⚠️  Some core service checks failed. Please review the errors above.")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
