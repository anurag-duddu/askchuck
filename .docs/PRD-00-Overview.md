# PRD-00: AskChuck Project Overview

## Document Information

| Field | Value |
|-------|-------|
| Project Name | AskChuck |
| Version | 2.0 |
| Author | Anurag Reddy |
| Created | January 2025 |
| Last Updated | January 2026 |
| Status | Ready for Implementation |

---

## Executive Summary

AskChuck is a Retrieval-Augmented Generation (RAG) system designed to make Charles Owen's Structured Planning methodology accessible through natural language conversation. Built on a corpus of 20 academic papers from IIT Institute of Design, the system enables students, researchers, and practitioners to explore Owen's systems thinking literature through an intelligent question-answering interface that retrieves relevant passages, displays explanatory figures, and synthesizes comprehensive responses grounded in the source material.

The project serves dual purposes: as a practical tool for learning Structured Planning methodology, and as a deep learning exercise in building production-quality RAG systems using modern best practices including hybrid retrieval, contextual chunking, cross-encoder reranking, and multimodal figure handling.

---

## Problem Statement

Charles Owen's Structured Planning methodology represents decades of refined thinking about human-centered innovation, documented across numerous papers, articles, and project reports. However, this knowledge is locked in PDF documents that are difficult to search, cross-reference, and synthesize. Key challenges include:

**For Users:**
- Owen's papers use specialized terminology (Function, Design Factor, Speculation, Information Structure) that requires understanding the full methodology to interpret correctly
- Concepts are interconnected across documents—understanding "Information Structure" requires context from papers on "Action Analysis," "VTCON," and "Means/Ends Analysis"
- Visual diagrams carry significant semantic content that text search cannot surface
- No existing tool provides conversational access to this knowledge base

**For the Builder (Learning Objectives):**
- Understanding end-to-end RAG pipeline construction from PDF ingestion to production deployment
- Implementing modern techniques: contextual chunking, hybrid retrieval, reranking, multimodal handling
- Building evaluation frameworks using RAGAS and LangSmith
- Deploying a production-quality application with authentication and observability

---

## Project Goals

### Primary Goals

1. **Build a functional RAG system** that accurately answers questions about Owen's Structured Planning methodology, grounded in the source documents

2. **Display relevant figures** alongside text responses, enabling users to understand visual concepts like Information Structures, Function Structures, and Abstraction Ladders

3. **Maintain conversation context** through chat sessions, allowing follow-up questions and deeper exploration of topics

4. **Deploy publicly** with Google OAuth authentication, enabling the academic community to access and use the system

### Secondary Goals

1. **Zero/minimal cost operation** using free tiers of Pinecone, Voyage AI, Cohere, Groq, and Cloudflare R2

2. **Comprehensive observability** through LangSmith tracing for debugging and improvement

3. **Evaluation framework** with golden dataset and RAGAS metrics for measuring system quality

4. **Clean, documented codebase** that demonstrates RAG best practices

5. **State-of-the-art retrieval** using hybrid search (dense + sparse), query expansion, and cross-encoder reranking

---

## Success Metrics

### Quantitative Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| RAGAS Faithfulness | > 0.80 | Automated evaluation on golden dataset |
| RAGAS Context Precision | > 0.70 | Automated evaluation on golden dataset |
| RAGAS Answer Relevancy | > 0.75 | Automated evaluation on golden dataset |
| Retrieval Hit Rate@5 | > 0.85 | Manual evaluation on 30 test queries |
| Figure Retrieval Accuracy | > 0.80 | Manual evaluation on visual queries |
| Response Latency (P95) | < 8 seconds | LangSmith trace analysis |
| Monthly Operating Cost | < $5 | API usage tracking |

### Qualitative Metrics

- Users can understand Owen's core concepts (Function, Design Factor, Information Structure) through conversation
- Responses correctly use Owen's specialized terminology
- Relevant figures are surfaced for visual concepts
- System gracefully handles out-of-scope questions
- Chat history enables meaningful multi-turn conversations

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           ASKCHUCK SYSTEM                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │   20 PDFs    │───▶│ PDF Parser   │───▶│  Processed   │               │
│  │  (Owen's     │    │   (TBD)      │    │    JSON      │               │
│  │  Literature) │    └──────────────┘    └──────┬───────┘               │
│  └──────────────┘                               │                        │
│                                                 ▼                        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │   PyMuPDF    │───▶│ Groq Vision  │───▶│   Figure     │               │
│  │   Figures    │    │ Descriptions │    │   Store      │──▶ Cloudflare │
│  └──────────────┘    └──────────────┘    └──────────────┘      R2       │
│                                                                          │
│  ┌──────────────────────────────────────────────────────┐               │
│  │                  CHUNKING LAYER                       │               │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐      │               │
│  │  │  Semantic  │  │ Contextual │  │  Owen      │      │               │
│  │  │  Chunker   │─▶│ Enrichment │─▶│ Glossary   │      │               │
│  │  │   (TBD)    │  │   (Groq)   │  │  Tagging   │      │               │
│  │  └────────────┘  └────────────┘  └────────────┘      │               │
│  └──────────────────────────────────────────────────────┘               │
│                              │                                           │
│                              ▼                                           │
│  ┌──────────────────────────────────────────────────────┐               │
│  │                  INDEXING LAYER                       │               │
│  │  ┌────────────┐                                       │               │
│  │  │ Voyage AI  │                                       │               │
│  │  │ Embeddings │                                       │               │
│  │  └─────┬──────┘                                       │               │
│  │        │                                              │               │
│  │        ▼                                              │               │
│  │  ┌────────────────────────────────┐                  │               │
│  │  │         Pinecone               │                  │               │
│  │  │  (Dense + Sparse Vectors)      │                  │               │
│  │  │    Native Hybrid Search        │                  │               │
│  │  └────────────────────────────────┘                  │               │
│  └──────────────────────────────────────────────────────┘               │
│                              │                                           │
│                              ▼                                           │
│  ┌──────────────────────────────────────────────────────┐               │
│  │                 RETRIEVAL LAYER                       │               │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐      │               │
│  │  │   Query    │  │  Pinecone  │  │  Cohere    │      │               │
│  │  │ Expansion  │─▶│   Hybrid   │─▶│  Reranker  │      │               │
│  │  │   (Groq)   │  │   Search   │  │            │      │               │
│  │  └────────────┘  └────────────┘  └────────────┘      │               │
│  └──────────────────────────────────────────────────────┘               │
│                              │                                           │
│                              ▼                                           │
│  ┌──────────────────────────────────────────────────────┐               │
│  │                GENERATION LAYER                       │               │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐      │               │
│  │  │   System   │─▶│   Groq     │─▶│  Response  │      │               │
│  │  │   Prompt   │  │ Llama 3.3  │  │ + Figures  │      │               │
│  │  └────────────┘  └────────────┘  └────────────┘      │               │
│  └──────────────────────────────────────────────────────┘               │
│                              │                                           │
│                              ▼                                           │
│  ┌──────────────────────────────────────────────────────┐               │
│  │                 FRONTEND LAYER                        │               │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐      │               │
│  │  │  Frontend  │  │    Auth    │  │    Chat    │      │               │
│  │  │   (TBD)    │  │   (TBD)    │  │  Sessions  │      │               │
│  │  └────────────┘  └────────────┘  └────────────┘      │               │
│  └──────────────────────────────────────────────────────┘               │
│                                                                          │
│  ┌──────────────────────────────────────────────────────┐               │
│  │               OBSERVABILITY LAYER                     │               │
│  │  ┌────────────┐  ┌────────────┐                      │               │
│  │  │ LangSmith  │  │   RAGAS    │                      │               │
│  │  │  Tracing   │  │   Evals    │                      │               │
│  │  └────────────┘  └────────────┘                      │               │
│  └──────────────────────────────────────────────────────┘               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Technology Stack Summary

| Layer | Technology | Rationale |
|-------|------------|-----------|
| PDF Parsing | TBD (see PRD-01) | Needs evaluation for caption detection reliability |
| Figure Extraction | PyMuPDF | Fast, preserves resolution, free |
| Figure Descriptions | Groq (Llama 3.2 Vision) | Free tier, vision-capable |
| Chunking | Semantic chunking (see PRD-03) | Intelligent boundary detection, not fixed-size |
| Contextual Enrichment | Groq (Llama 3.3 70B) | Free tier, fast inference |
| Embeddings | **Voyage AI (voyage-3)** | Best-in-class for RAG, free 200M tokens/month |
| Vector Database | **Pinecone (Serverless)** | Free tier: 2GB storage, unlimited queries, native hybrid search |
| Hybrid Search | Pinecone Native | Dense + sparse vectors in single query, built-in fusion |
| Query Expansion | Groq (Llama 3.3 70B) | Expands queries with Owen terminology |
| Reranking | **Cohere (rerank-v3.0)** | Free tier (1000/month), model diversity from embeddings |
| Generation | Groq (Llama 3.3 70B) | Free tier, fast, good reasoning |
| Figure Storage | **Cloudflare R2** | Free 10GB, 1M requests/month |
| Frontend | TBD (see PRD-07) | Evaluating production-grade alternatives |
| Authentication | TBD (see PRD-07) | WorkOS, Auth0, or Clerk |
| Hosting | TBD (see PRD-09) | Own domain, production-grade |
| Observability | LangSmith | Free tier, comprehensive tracing |
| Evaluation | RAGAS | Standard RAG metrics, open source |

### SOTA Techniques

| Technique | Purpose | Implementation |
|-----------|---------|----------------|
| Hybrid Search | Captures both semantic and lexical matches | Pinecone native (dense + sparse vectors) |
| Contextual Enrichment | Improves embedding quality by adding document context | Groq LLM prepends context to chunks |
| Query Expansion | Bridges vocabulary gap between user queries and Owen's terminology | Groq LLM expands queries |
| Cross-Encoder Reranking | Precise relevance scoring after initial retrieval | Cohere rerank-v3.0 |
| Structured Figure Retrieval | Surfaces relevant diagrams for visual concepts | Separate figure matching logic |

---

## Project Structure

```
askchuck/
├── .env                          # API keys (gitignored)
├── .env.example                  # Template for collaborators
├── .gitignore                    # Git ignore rules
├── requirements.txt              # Python dependencies
├── pyproject.toml                # Project metadata
├── README.md                     # Project documentation
│
├── .streamlit/
│   ├── config.toml               # Streamlit configuration
│   └── secrets.toml              # Secrets for deployment (gitignored)
│
├── data/
│   ├── raw/                      # Original 20 PDFs
│   ├── processed/                # Parsed document JSONs
│   ├── chunks/                   # Chunked content with metadata
│   └── figures/                  # Extracted figure images
│
├── src/
│   ├── __init__.py
│   │
│   ├── ingestion/                # Document processing
│   │   ├── __init__.py
│   │   ├── pdf_parser.py         # PDF parsing (library TBD)
│   │   ├── figure_extractor.py   # PyMuPDF figure extraction
│   │   └── figure_describer.py   # Groq Vision descriptions
│   │
│   ├── chunking/                 # Text chunking
│   │   ├── __init__.py
│   │   ├── chunker.py            # Semantic chunking
│   │   └── contextual_enrichment.py  # Context prefix generation
│   │
│   ├── indexing/                 # Index building
│   │   ├── __init__.py
│   │   ├── embeddings.py         # Voyage AI embedding generation
│   │   └── vector_store.py       # Pinecone operations
│   │
│   ├── retrieval/                # Retrieval pipeline
│   │   ├── __init__.py
│   │   ├── query_expansion.py    # Query expansion with Owen terminology
│   │   ├── hybrid_retriever.py   # Pinecone hybrid search wrapper
│   │   └── reranker.py           # Cohere reranking
│   │
│   ├── generation/               # Response generation
│   │   ├── __init__.py
│   │   ├── prompts.py            # System and user prompts
│   │   └── rag_chain.py          # Full RAG pipeline
│   │
│   └── utils/                    # Shared utilities
│       ├── __init__.py
│       ├── config.py             # Configuration management
│       ├── cloudflare_client.py  # Cloudflare R2 operations
│       └── owen_glossary.py      # Owen terminology definitions
│
├── scripts/
│   ├── ingest_all.py             # Process all PDFs
│   ├── build_index.py            # Build Pinecone index with hybrid vectors
│   ├── upload_figures.py         # Upload figures to Cloudflare R2
│   └── run_evaluation.py         # Run RAGAS evaluation
│
├── tests/
│   ├── __init__.py
│   ├── test_retrieval.py         # Retrieval unit tests
│   ├── test_generation.py        # Generation tests
│   └── golden_dataset.json       # Evaluation QA pairs
│
└── app.py                        # Streamlit application entry point
```

---

## Document Corpus Overview

The V1 corpus consists of 20 papers by Charles Owen from IIT Institute of Design. These papers form an interconnected series on Structured Planning methodology. Key documents include:

| Document | Primary Topics | Key Concepts Introduced |
|----------|---------------|------------------------|
| Context for Creativity (1991) | Structured Planning overview | Design Factor, Speculation, Action Analysis, VTCON, Information Structure |
| The Power of Abstraction (2009) | Abstraction techniques | Abstraction Ladder, Abstraction Structure, Means/Ends Analysis |
| Bottom-up, Top-down (2009) | Innovation approaches | Top-down vs bottom-up synthesis, composite approach |
| Design Thinking: Driving Innovation | Design philosophy | Human-centered innovation, design thinking principles |
| Covering User Needs | Requirements gathering | Function Structure, user needs analysis |
| Insight and Ideas | Ideation | Design Factors, insight capture |
| Capturing Ideas | Idea documentation | Speculation format, Design Implications |
| Using the Tools of Structure | Structuring methods | RELATN, VTCON, clustering |
| Organizing for Innovation | Organization | Information Structure creation, team organization |
| The Systems Viewpoint | Systems thinking | Systems approach, holistic design |
| [Additional 10 documents] | Various | Supporting concepts and applications |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Groq rate limits exceeded | Medium | High | Implement backoff, cache responses, batch processing for ingestion |
| Voyage AI rate limits | Low | Low | 200M tokens/month is generous for 20 documents |
| Cohere free tier exhausted | Low | Medium | 1000 calls/month should suffice; can disable reranking as fallback |
| Pinecone free tier limits | Very Low | Low | 2GB storage, unlimited queries - well within limits for 20 papers |
| Poor retrieval for specialized terms | Medium | High | BM25 hybrid retrieval, Owen glossary injection, query expansion |
| Figure descriptions miss key content | Medium | Medium | Iterate on vision prompt, add human review for critical figures |
| Cloudflare R2 configuration issues | Low | Low | Well-documented API, S3-compatible |
| Frontend/Auth complexity | Medium | Medium | Evaluate options carefully in PRD-07; start simple |

---

## Implementation Phases

| Phase | PRD Reference | Duration | Dependencies |
|-------|---------------|----------|--------------|
| 0. Environment Setup | PRD-01 | 30 min | None |
| 1. Document Ingestion | PRD-02 | 2-3 hrs | Phase 0 |
| 2. Chunking & Enrichment | PRD-03 | 2 hrs | Phase 1 |
| 3. Indexing | PRD-04 | 1.5 hrs | Phase 2 |
| 4. Retrieval Pipeline | PRD-05 | 2 hrs | Phase 3 |
| 5. Generation Chain | PRD-06 | 1.5 hrs | Phase 4 |
| 6. Frontend | PRD-07 | 2-3 hrs | Phase 5 |
| 7. Evaluation | PRD-08 | 1 hr | Phase 6 |
| 8. Deployment | PRD-09 | 1 hr | Phase 7 |

**Total Estimated Duration: 14-16 hours**

---

## Appendix: Related PRD Documents

1. **PRD-01-Environment-Setup.md** - Development environment, dependencies, API accounts
2. **PRD-02-Document-Ingestion.md** - PDF parsing, figure extraction, description generation
3. **PRD-03-Chunking-Enrichment.md** - Chunking strategy, contextual enrichment, glossary
4. **PRD-04-Indexing.md** - Embeddings, Pinecone vector store with hybrid search
5. **PRD-05-Retrieval.md** - Pinecone hybrid search, query expansion, Cohere reranking
6. **PRD-06-Generation.md** - RAG chain, prompts, response formatting
7. **PRD-07-Frontend.md** - Streamlit app, authentication, chat interface
8. **PRD-08-Evaluation.md** - Golden dataset, RAGAS metrics, testing strategy
9. **PRD-09-Deployment.md** - Streamlit Cloud deployment, secrets management
