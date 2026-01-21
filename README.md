# AskChuck

**A Retrieval-Augmented Generation (RAG) system for Prof. Charles Owen's Structured Planning methodology**

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Pinecone](https://img.shields.io/badge/Pinecone-000000?style=flat)](https://www.pinecone.io/)
[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)

---

## Overview

AskChuck makes Charles Owen's Structured Planning methodology accessible through natural language conversation. Built on a corpus of 20 academic papers from IIT Institute of Design, the system enables students, researchers, and practitioners to explore Owen's systems thinking literature through an intelligent question-answering interface.

### Key Features

- **📚 Intelligent Q&A**: Ask questions about Owen's Structured Planning methodology and get accurate, source-grounded answers
- **🖼️ Multimodal Retrieval**: Retrieves relevant figures and diagrams alongside text responses
- **💬 Conversational Interface**: Maintains chat history for multi-turn conversations with contextual follow-ups
- **🔍 Hybrid Search**: Combines dense and sparse retrieval for optimal accuracy across semantic and lexical queries
- **⚡ Production-Grade**: Built with state-of-the-art RAG techniques including contextual chunking, reranking, and query expansion

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        ASKCHUCK SYSTEM                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  📄 Document Ingestion                                          │
│  ├── 20 PDFs (Owen's Literature)                                │
│  ├── PDF Parser → Processed JSON                                │
│  └── Figure Extraction (PyMuPDF) → Groq Vision Descriptions     │
│                                                                  │
│  ✂️ Chunking & Enrichment                                       │
│  ├── Semantic Chunking                                          │
│  ├── Contextual Enrichment (Groq LLM)                           │
│  └── Owen Glossary Tagging                                      │
│                                                                  │
│  🗄️ Indexing Layer                                              │
│  ├── Voyage AI Embeddings (voyage-3)                            │
│  └── Pinecone Vector Database (Hybrid: Dense + Sparse)          │
│                                                                  │
│  🔍 Retrieval Pipeline                                          │
│  ├── Query Expansion (Groq LLM)                                 │
│  ├── Pinecone Hybrid Search                                     │
│  └── Cohere Cross-Encoder Reranking                             │
│                                                                  │
│  ✨ Generation Layer                                            │
│  ├── Groq (Llama 3.3 70B)                                       │
│  └── Response + Figure URLs                                     │
│                                                                  │
│  🌐 API & Storage                                               │
│  ├── FastAPI Backend                                            │
│  ├── Firebase (Auth & Chat History)                             │
│  └── Cloudflare R2 (Figure Storage)                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Backend** | FastAPI | High-performance async API framework |
| **Vector Database** | Pinecone (Serverless) | Hybrid search with dense + sparse vectors |
| **Embeddings** | Voyage AI (voyage-3) | State-of-the-art RAG embeddings |
| **LLM Generation** | Groq (Llama 3.3 70B) | Fast inference for generation & enrichment |
| **Reranking** | Cohere (rerank-v3.0) | Cross-encoder reranking for precision |
| **Vision** | Groq (Llama 3.2 Vision) | Figure description generation |
| **Authentication** | Firebase Admin SDK | User management & session handling |
| **Figure Storage** | Cloudflare R2 | S3-compatible object storage |
| **Observability** | LangSmith | Tracing and debugging |

---

## Project Structure

```
askchuck/
├── .env                          # API keys (gitignored)
├── .gitignore                    # Git ignore rules
├── .mcp.json                     # Model Context Protocol config
├── README.md                     # This file
│
├── .docs/                        # Detailed PRDs
│   ├── PRD-00-Overview.md        # Project overview & architecture
│   ├── PRD-01-Environment-Setup.md
│   ├── PRD-02-Document-Ingestion.md
│   ├── PRD-03-Chunking-Enrichment.md
│   ├── PRD-04-Indexing.md
│   ├── PRD-05-Retrieval.md
│   ├── PRD-06-Generation.md
│   ├── PRD-07-Frontend.md
│   ├── PRD-08-Evaluation.md
│   └── PRD-09-Deployment.md
│
├── ask_chuck_api/               # FastAPI application
│   ├── ask_chuck_api/
│   │   ├── main.py              # API entry point
│   │   ├── auth/                # Authentication logic
│   │   └── rag/                 # RAG system components
│   │       ├── constants.py
│   │       ├── data_ingestion_system.py
│   │       ├── handle_query.py
│   │       ├── handle_conversation.py
│   │       ├── rag_chain.py
│   │       ├── rag_chat_history.py
│   │       └── serving_system.py
│   ├── requirements.txt         # Python dependencies
│   ├── Dockerfile               # Container configuration
│   └── tests/                   # API tests
│
├── Charles Owen Papers/         # Source PDFs
├── figure_extraction_test/      # Figure extraction experiments
├── evaluate_pdf_extraction.py   # PDF parsing evaluation
├── inspect_pdf_graphics.py      # PDF graphics inspection tool
└── test_figure_rendering.py     # Figure rendering tests
```

---

## Getting Started

### Prerequisites

- Python 3.9+
- API keys for:
  - [Pinecone](https://www.pinecone.io/)
  - [Voyage AI](https://www.voyageai.com/)
  - [Groq](https://groq.com/)
  - [Cohere](https://cohere.com/)
  - [Cloudflare R2](https://www.cloudflare.com/products/r2/)
  - Firebase (for authentication)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/anurag-duddu/askchuck.git
   cd askchuck
   ```

2. **Set up environment variables**
   ```bash
   cp ask_chuck_api/sample_env.txt .env
   # Edit .env with your API keys
   ```

3. **Install dependencies**
   ```bash
   cd ask_chuck_api
   pip install -r requirements.txt
   ```

4. **Run the API server**
   ```bash
   uvicorn ask_chuck_api.main:app --reload
   ```

   The API will be available at [http://localhost:8000](http://localhost:8000)

---

## API Endpoints

### `GET /`
Health check endpoint

**Response:**
```json
{
  "message": "Hello World"
}
```

### `GET /query`
Single-turn question answering

**Parameters:**
- `query` (string): The question to ask

**Response:**
```json
{
  "answer": "...",
  "sources": [...],
  "figures": [...]
}
```

### `GET /converse`
Multi-turn conversational interface with chat history

**Parameters:**
- `query` (string): The question to ask
- `session_id` (string): Chat session identifier
- `user_id` (string): User identifier

**Response:**
```json
{
  "answer": "...",
  "sources": [...],
  "figures": [...],
  "session_id": "..."
}
```

### `GET /ingest`
Ingest a new document into the knowledge base

**Parameters:**
- `url` (string): URL to the PDF document
- `title` (string): Document title

---

## RAG Pipeline Details

### 1. **Document Ingestion**
- Extracts text and figures from PDFs using PyMuPDF
- Generates figure descriptions using Groq Vision (Llama 3.2)
- Stores figures in Cloudflare R2

### 2. **Chunking & Enrichment**
- Semantic chunking for intelligent boundary detection
- Contextual enrichment adds document context to each chunk
- Owen glossary tagging for specialized terminology

### 3. **Hybrid Search**
- Dense vectors (Voyage AI embeddings) for semantic similarity
- Sparse vectors for lexical/keyword matching
- Pinecone native hybrid search with automatic fusion

### 4. **Reranking**
- Cohere cross-encoder reranking for precision
- Ranks retrieved chunks by relevance to query

### 5. **Generation**
- Groq Llama 3.3 70B for answer synthesis
- Grounded in retrieved sources
- Returns relevant figures with responses

---

## Development Roadmap

See [.docs/PRD-REVIEW-TRACKER.md](.docs/PRD-REVIEW-TRACKER.md) for detailed implementation status.

**Completed:**
- ✅ Document ingestion pipeline
- ✅ FastAPI backend with authentication
- ✅ RAG chain implementation
- ✅ Conversational interface with chat history
- ✅ Pinecone integration

**In Progress:**
- 🔨 Frontend development
- 🔨 Evaluation framework (RAGAS)
- 🔨 Production deployment

**Planned:**
- 📋 Query expansion with Owen terminology
- 📋 Contextual chunk enrichment
- 📋 Cross-encoder reranking
- 📋 Figure retrieval optimization

---

## Evaluation Metrics

| Metric | Target | Status |
|--------|--------|--------|
| RAGAS Faithfulness | > 0.80 | Pending |
| RAGAS Context Precision | > 0.70 | Pending |
| RAGAS Answer Relevancy | > 0.75 | Pending |
| Retrieval Hit Rate@5 | > 0.85 | Pending |
| Figure Retrieval Accuracy | > 0.80 | Pending |
| Response Latency (P95) | < 8s | Pending |

---

## Contributing

This is a learning project for building production-quality RAG systems. Contributions, suggestions, and feedback are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## Documentation

Detailed documentation is available in the [.docs/](.docs/) directory:

- **[PRD-00-Overview.md](.docs/PRD-00-Overview.md)** - Project overview, architecture, and goals
- **[PRD-02-Document-Ingestion.md](.docs/PRD-02-Document-Ingestion.md)** - PDF parsing and figure extraction
- **[PRD-04-Indexing.md](.docs/PRD-04-Indexing.md)** - Vector database setup
- **[PRD-05-Retrieval.md](.docs/PRD-05-Retrieval.md)** - Hybrid search and reranking
- **[PRD-06-Generation.md](.docs/PRD-06-Generation.md)** - RAG chain and prompts

---

## License

MIT License - see LICENSE file for details

---

## Acknowledgments

- **Prof. Charles Owen** - For his groundbreaking work on Structured Planning methodology
- **IIT Institute of Design** - For the academic papers that form this knowledge base
- Built with modern RAG best practices from the AI research community

---

---

## Quick Start (New Implementation)

The project has been rebuilt following PRD-01 through PRD-07:

### Run Streamlit UI
```bash
# Install dependencies
pip install -r requirements.txt

# Set up .env file with API keys
cp .env.example .env
# Edit .env with your keys

# Run Streamlit app
bash scripts/run_streamlit.sh
# Or: streamlit run streamlit_app.py
```

### Run FastAPI Server
```bash
# Start the API server
bash scripts/run_api.sh
# Or: python -m uvicorn src.api.server:app --reload

# API docs available at: http://localhost:8000/docs
```

### Run the Full Pipeline
```bash
# 1. Ingest documents
python scripts/ingest_documents.py --all

# 2. Chunk and enrich
python scripts/chunk_documents.py --all

# 3. Build index
python scripts/build_index.py --all

# 4. Run Streamlit UI
streamlit run streamlit_app.py
```

---

**Built with ❤️ for learning production-quality RAG systems**
