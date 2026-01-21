# PRD-02 Document Ingestion - Implementation Status

## ✅ Completed Components

- [x] **PDF Parser** (`src/ingestion/pdf_parser.py`)
  - PyMuPDF-based text extraction
  - Block-level sorting for reading order (handles two-column layouts)
  - Metadata extraction (title, author, date, source)
  - Heuristic section detection using font sizes
  - JSON output generation

- [x] **Figure Extractor** (`src/ingestion/figure_extractor.py`)
  - Page region rendering at 300 DPI for vector graphics
  - Caption detection using regex patterns
  - Heuristic bounding box estimation
  - Support for single and two-column layouts
  - High-quality PNG output

- [x] **Figure Describer** (`src/ingestion/figure_describer.py`)
  - Groq Vision API integration (Llama 3.2 Vision)
  - Owen-specific terminology in prompts
  - Batch processing with rate limiting
  - Fallback handling for API failures

- [x] **R2 Uploader** (`src/ingestion/figure_uploader.py`) **(Optional)**
  - Cloudflare R2 (S3-compatible) upload
  - Public URL generation
  - Graceful degradation if not configured
  - Batch processing with error handling

- [x] **Main Pipeline** (`src/ingestion/pipeline.py`)
  - Orchestrates all components
  - Progress tracking with tqdm
  - Flexible skip options for each stage
  - Comprehensive error handling and logging

- [x] **CLI Script** (`scripts/ingest_documents.py`)
  - Process single PDF or batch
  - Multiple processing modes
  - Command-line argument parsing

## 📋 Manual Steps Required

### 1. Install Dependencies

The ingestion pipeline requires several dependencies. Install them now:

```bash
# Activate virtual environment
source venv/bin/activate

# Install requirements (if not done in PRD-01)
pip install -r requirements.txt
```

**Key dependencies for ingestion:**
- `pymupdf` (PDF parsing and rendering)
- `pillow` (Image processing)
- `groq` (Vision API)
- `boto3` (R2 upload - optional)
- `tqdm` (Progress bars)

### 2. Prepare PDF Files

Ensure Owen's papers are in `data/raw/`:

```bash
# Check if PDFs are in place
ls -la data/raw/*.pdf | wc -l

# If not, copy from "Charles Owen Papers/" folder
cp "Charles Owen Papers/"*.pdf data/raw/
```

### 3. Test on Sample PDFs

Before processing all documents, test on a few:

```bash
# Process first 2 PDFs (default test mode)
python scripts/ingest_documents.py

# Or specify limit explicitly
python scripts/ingest_documents.py --limit 2
```

**Verify outputs:**
```bash
# Check processed JSON
ls data/processed/
cat data/processed/<first_doc>.json | head -100

# Check extracted figures
ls data/figures/
```

### 4. Process All Documents

Once testing passes, process the full corpus:

```bash
# Process all PDFs with full pipeline
python scripts/ingest_documents.py --all

# Or skip optional stages:
python scripts/ingest_documents.py --all --skip-upload  # Skip R2 upload
python scripts/ingest_documents.py --all --skip-descriptions  # Skip Vision API
python scripts/ingest_documents.py --all --skip-figures  # Text only
```

**Expected results:**
- ~20 JSON files in `data/processed/`
- 30-50+ PNG files in `data/figures/`
- Each JSON contains text, sections, figures with descriptions

### 5. (Optional) Configure Cloudflare R2

If you want figure hosting:

1. Set up R2 bucket (see `docs/SETUP_COMPLETE.md`)
2. Update `.env` with R2 credentials
3. Rerun pipeline WITHOUT `--skip-upload` flag

R2 URLs will be added to figure metadata.

## 🎯 Current Status

### Core Pipeline ✅ READY
All ingestion components implemented and ready to use.

### Processing Status ⏳ PENDING USER ACTION
- **Dependency installation**: Required (manual step)
- **PDF files**: Should be in `data/raw/`
- **Test run**: Not yet executed
- **Full processing**: Not yet executed

### Optional Components
- **R2 Upload**: Implemented but not required
  - Can use local `file://` paths if R2 not configured
  - Figures work fine stored locally for development

## 📊 Output Schema

Each processed document generates JSON with:

```json
{
  "document_id": "owen_power_of_abstraction_2009",
  "metadata": {
    "title": "The Power of Abstraction",
    "author": "Charles L. Owen",
    "publication_date": "August 2009",
    "source": "Business Process Management Institute",
    "filename": "abstract09.pdf",
    "total_pages": 9,
    "processed_at": "2026-01-20T12:00:00Z"
  },
  "sections": [
    {
      "heading": "Abstract",
      "level": 1,
      "content": "In the innovator's tool box...",
      "page_start": 3,
      "page_end": 3
    }
  ],
  "figures": [
    {
      "figure_id": "owen_power_of_abstraction_2009_fig_1",
      "figure_number": 1,
      "page": 4,
      "caption": "An Abstraction Ladder...",
      "local_path": "data/figures/owen_power_of_abstraction_2009_fig_1.png",
      "cloudflare_url": null,
      "description": "This figure shows a hierarchical Abstraction Ladder...",
      "bbox": [72, 150, 540, 450],
      "width": 1985,
      "height": 1022
    }
  ],
  "full_text": "The Power of Abstraction\n\nCharles L. Owen..."
}
```

## ⏭️ Next Steps

### Option 1: Test Ingestion Now

Install dependencies and run test ingestion:

```bash
source venv/bin/activate
pip install -r requirements.txt
python scripts/ingest_documents.py --limit 2
```

### Option 2: Continue to PRD-03 (Chunking)

The chunking module can be implemented while dependencies install. It will consume the JSON output from this pipeline.

### Option 3: Full Batch Processing

Process all 20 documents and move to next PRD:

```bash
python scripts/ingest_documents.py --all
# Then proceed to PRD-03
```

## 🔧 Troubleshooting

### ImportError for pymupdf/fitz
```bash
pip install pymupdf pillow
```

### Groq API Rate Limits
- Free tier: 30 RPM for vision model
- Use `--skip-descriptions` to bypass temporarily
- Add delays between batches if needed

### R2 Upload Fails
- Check `.env` credentials are correct
- Verify bucket exists in R2 dashboard
- Use `--skip-upload` to bypass and use local paths

### No PDFs Found
```bash
# Verify PDFs in correct location
ls "Charles Owen Papers/"
cp "Charles Owen Papers/"*.pdf data/raw/
```

## 📚 References

- **Implementation Plan**: `docs/plans/2026-01-20-document-ingestion.md`
- **PRD Specification**: `.docs/PRD-02-Document-Ingestion.md`
- **Evaluation Findings**: `.docs/PDF-EXTRACTION-EVALUATION-FINDINGS.md`
- **Code Modules**: `src/ingestion/`

---

**Document Ingestion Pipeline: READY FOR USE ✅**

Awaiting user to install dependencies and process documents!
