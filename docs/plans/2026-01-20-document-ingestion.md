# PRD-02: Document Ingestion Implementation Plan

**Goal:** Build document ingestion pipeline to process Owen's PDFs into structured JSON with text, figures, and metadata

**Architecture:** Modular pipeline with separate components for PDF parsing, figure extraction, vision descriptions, and cloud storage

**Tech Stack:** PyMuPDF (text + figures), Groq Vision (descriptions), Cloudflare R2 (storage - optional)

---

## Task 1: Create PDF Parser (PyMuPDF-based)

**Files:**
- Create: `src/ingestion/pdf_parser.py`

**Implementation:**
Use PyMuPDF for text extraction instead of Docling (simpler, no additional dependencies)

**Steps:**

1. Create `src/ingestion/pdf_parser.py` with OwenPDFParser class
2. Implement `parse_document()` method using PyMuPDF
3. Extract text with block-level sorting for reading order
4. Extract metadata (title, author, date, source)
5. Generate document ID from filename
6. Test on one sample PDF

**Verification:**
```bash
python -c "from src.ingestion.pdf_parser import OwenPDFParser; parser = OwenPDFParser(); result = parser.parse_document('data/raw/<first_pdf>.pdf'); print(f'Extracted {len(result[\"full_text\"])} characters')"
```

**Commit:** `feat: add PDF parser with PyMuPDF`

---

## Task 2: Create Figure Extractor (Page Rendering)

**Files:**
- Create: `src/ingestion/figure_extractor.py`

**Implementation:**
Extract figures via page rendering at 300 DPI (handles vector graphics)

**Steps:**

1. Create `src/ingestion/figure_extractor.py` with FigureExtractor class
2. Implement caption detection using regex for "Figure N"
3. Implement bounding box estimation (heuristic approach)
4. Implement page region rendering at 300 DPI
5. Save figures as PNG with consistent naming
6. Test on sample PDF with known figures

**Verification:**
```bash
python -c "from src.ingestion.figure_extractor import FigureExtractor; extractor = FigureExtractor(); figures = extractor.extract_figures('data/raw/<pdf_with_figures>.pdf', 'test_doc'); print(f'Extracted {len(figures)} figures')"
ls data/figures/
```

**Commit:** `feat: add figure extractor with page rendering`

---

## Task 3: Create Figure Describer (Groq Vision)

**Files:**
- Create: `src/ingestion/figure_describer.py`

**Implementation:**
Generate semantic descriptions for figures using Groq Vision API

**Steps:**

1. Create `src/ingestion/figure_describer.py` with FigureDescriber class
2. Implement Groq Vision API integration
3. Create prompt template for Owen-specific figure description
4. Add rate limiting and retry logic
5. Test with sample figure

**Verification:**
```bash
python -c "from src/ingestion.figure_describer import FigureDescriber; describer = FigureDescriber(); desc = describer.describe_figure('data/figures/<first_figure>.png', 'Test Caption'); print(desc[:200])"
```

**Commit:** `feat: add figure describer with Groq Vision`

---

## Task 4: Create Cloudflare R2 Uploader (Optional)

**Files:**
- Create: `src/ingestion/figure_uploader.py`

**Implementation:**
Upload figures to Cloudflare R2 and get public URLs

**Steps:**

1. Create `src/ingestion/figure_uploader.py` with R2Uploader class
2. Implement boto3 S3-compatible upload
3. Generate public URLs
4. Add error handling and retry logic
5. Test with sample figure (if R2 credentials available)

**Verification:**
```bash
# Only if R2 credentials are set
python -c "from src.ingestion.figure_uploader import R2Uploader; uploader = R2Uploader(); url = uploader.upload_figure('data/figures/<figure>.png', '<figure_id>'); print(url)"
```

**Commit:** `feat: add Cloudflare R2 figure uploader`

**Note:** This task is OPTIONAL - can skip if R2 not configured. Figures can be stored locally with file:// URLs.

---

## Task 5: Create Main Ingestion Pipeline

**Files:**
- Create: `src/ingestion/pipeline.py`
- Create: `scripts/ingest_documents.py`

**Implementation:**
Orchestrate all components into complete pipeline

**Steps:**

1. Create `src/ingestion/pipeline.py` with DocumentIngestionPipeline class
2. Integrate pdf_parser, figure_extractor, figure_describer
3. Optionally integrate figure_uploader (if configured)
4. Generate final JSON output per PRD schema
5. Create `scripts/ingest_documents.py` CLI script
6. Add progress logging with tqdm
7. Test full pipeline on 1-2 sample PDFs

**Verification:**
```bash
python scripts/ingest_documents.py --limit 2
ls data/processed/
cat data/processed/<first_doc>.json | head -50
```

**Commit:** `feat: add main document ingestion pipeline`

---

## Task 6: Process All Documents

**Files:**
- None (execution only)

**Implementation:**
Run pipeline on all 20 PDFs

**Steps:**

1. Ensure all PDFs are in `data/raw/`
2. Run full ingestion pipeline
3. Verify all JSON outputs
4. Check figure extraction count
5. Spot-check a few descriptions
6. Generate summary statistics

**Verification:**
```bash
python scripts/ingest_documents.py --all
ls -la data/processed/ | wc -l  # Should be ~20
ls -la data/figures/ | wc -l    # Should be 30-50+ figures
```

**Commit:** `chore: process all 20 Owen documents`

---

## Task 7: Documentation

**Files:**
- Create: `docs/INGESTION_COMPLETE.md`

**Implementation:**
Document ingestion results and next steps

**Commit:** `docs: add ingestion completion summary`

---

## Acceptance Criteria

| Criterion | Verification |
|-----------|-------------|
| ✅ All 20 PDFs parsed | 20 JSON files in `data/processed/` |
| ✅ Text extraction works | JSON files contain structured text |
| ✅ Figures extracted | 30+ PNG files in `data/figures/` |
| ✅ Figure descriptions generated | JSON contains vision model descriptions |
| ✅ Metadata captured | JSON includes title, author, date |
| ⊘ Figures uploaded to R2 (optional) | URLs in JSON if configured |
| ✅ Output schema matches PRD | JSON structure validated |
| ✅ No processing errors | All PDFs processed successfully |

---

## Notes

- PyMuPDF approach is simpler than Docling (no heavy dependencies)
- Figure extraction via page rendering handles vector graphics
- R2 upload is optional - can use local file:// URLs
- Can process in batches if rate limits hit
- Sample PDFs should be tested first before batch processing

---

## Alternative: Simplified First Pass

If encountering complexity, consider this simplified approach for MVP:

1. Extract text only (skip figures temporarily)
2. Use simple block-level text extraction
3. Save raw text to JSON
4. Add figure extraction in second iteration

This gets basic text ingestion working quickly, then enhances with figures.
