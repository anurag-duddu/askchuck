# AskChuck Documentation Index

This directory contains all Product Requirement Documents (PRDs) for the AskChuck RAG system.

## Documentation Status

| Document | Status | Last Updated |
|----------|--------|--------------|
| [PRD-00-Overview.md](PRD-00-Overview.md) | ✅ Complete | January 2026 |
| [PRD-01-Environment-Setup.md](PRD-01-Environment-Setup.md) | ✅ Finalized | January 2026 |
| [PRD-02-Document-Ingestion.md](PRD-02-Document-Ingestion.md) | ✅ Updated | January 2026 |
| [PRD-03-Chunking-Enrichment.md](PRD-03-Chunking-Enrichment.md) | 📝 Draft | - |
| [PRD-04-Indexing.md](PRD-04-Indexing.md) | 📝 Draft | - |
| [PRD-05-Retrieval.md](PRD-05-Retrieval.md) | 📝 Draft | - |
| [PRD-06-Generation.md](PRD-06-Generation.md) | 📝 Draft | - |
| [PRD-07-Frontend.md](PRD-07-Frontend.md) | 📝 Draft | - |
| [PRD-08-Evaluation.md](PRD-08-Evaluation.md) | 📝 Draft | - |
| [PRD-09-Deployment.md](PRD-09-Deployment.md) | 📝 Draft | - |

## Key Updates (January 2026)

### PDF Extraction Evaluation Complete ✅

**Key Finding:** Owen's papers contain vector graphics, not embedded images.

**Solution:** Page rendering at 300 DPI using PyMuPDF.

**Documentation:**
- [PDF-EXTRACTION-EVALUATION-FINDINGS.md](PDF-EXTRACTION-EVALUATION-FINDINGS.md) - Detailed evaluation results
- [PRD-01-Environment-Setup.md](PRD-01-Environment-Setup.md) - Updated with finalized approach
- [PRD-02-Document-Ingestion.md](PRD-02-Document-Ingestion.md) - Updated implementation code

**Technology Stack Changes:**
| Component | Previous (PRD v1.0) | Current (PRD v2.0) |
|-----------|---------------------|-------------------|
| Embeddings | HuggingFace/BGE (local) | Voyage AI (API) |
| Vector DB | ChromaDB (local) | Pinecone (cloud, hybrid search) |
| File Storage | Supabase | Cloudflare R2 |
| Authentication | Google OAuth | Clerk |
| PDF Parsing | Docling (tentative) | PyMuPDF page rendering (finalized) |

## Quick Start

1. **Environment Setup:** Follow [PRD-01-Environment-Setup.md](PRD-01-Environment-Setup.md)
2. **PDF Evaluation:** See [PDF-EXTRACTION-EVALUATION-FINDINGS.md](PDF-EXTRACTION-EVALUATION-FINDINGS.md)
3. **Implementation:** Proceed with [PRD-02-Document-Ingestion.md](PRD-02-Document-Ingestion.md)

## Evaluation Artifacts

Located in project root (gitignored):
- `evaluate_pdf_extraction.py` - Main evaluation script
- `inspect_pdf_graphics.py` - Deep graphics inspection
- `test_figure_rendering.py` - Proof-of-concept renderer
- `figure_extraction_test/` - Extracted sample figures

## Next Steps

✅ **Completed:**
- PDF extraction approach evaluation
- Technology stack finalization
- PRD-01 and PRD-02 updates

📋 **Ready for Implementation:**
- Begin PRD-02: Document Ingestion phase
- Process all 20 Owen papers
- Extract figures at 300 DPI
- Generate vision descriptions
- Upload to Cloudflare R2

## Notes

- All PRDs use Cloudflare R2 (not Supabase) for figure storage
- All PRDs use Voyage AI (not HuggingFace/BGE) for embeddings
- All PRDs use Pinecone (not ChromaDB) for vector storage
- PDF extraction uses page rendering, not image extraction
