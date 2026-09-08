# Fact Knowledge Layer

An AI-powered system that extracts structured factual claims from unstructured PDF documents, grounds every fact in verifiable source evidence (page number and exact text excerpt), and identifies cross-document relationships—discovering corroborations, genuine contradictions, and apparent contradictions reconciled through contextual dimensions (such as time scopes, reporting bases, or units).

Built for the **Superjoin Engineering Intern Assignment (VIT 2026)**.

---

## Architecture & Pipeline

```text
                  PDF Documents
                       │
                       ▼
          PyMuPDF Layout & Block Parsing
                       │
                       ▼
          Logical Page Normalization
           (Detects & splits 2-up PDFs)
                       │
                       ▼
             Layout-Aware Chunker
       (Groups blocks up to ~1,500 chars)
                       │
                       ▼
        Regex Fact-Bearing Pre-Filter
        (Cuts ~50% of non-fact chunks)
                       │
                       ▼
           Gemini Structured Extraction
         (Batch size: 5 chunks per call)
         - Entity (Canonicalized)
         - Attribute & Value
         - Time Scope & Unit
         - Context Qualifiers (Standalone/Consolidated)
         - Raw Source Evidence Quote
                       │
                       ▼
       PostgreSQL + pgvector Fact Storage
            (Deduplication & Storage)
                       │
                       ▼
          Fact Embedding Generation
             (gemini-embedding-001)
                       │
                       ▼
            Cross-Document Candidate Search
     (pgvector Cosine Distance + Structural Reranking)
                       │
                       ▼
        LLM Comparative Reasoning Engine
   ┌───────────────────┼───────────────────┐
   ▼                   ▼                   ▼
Corroborates     Contradicts     Context-Explained
```

---

## Setup and Run Instructions

### 1. Prerequisites
- **Python**: 3.11 or 3.12
- **Docker & Docker Compose**: For running PostgreSQL with `pgvector`
- **Google Gemini API Key**: [Get an API key here](https://aistudio.google.com/)

### 2. Clone and Configure
```bash
git clone https://github.com/<your-username>/fact-knowledge-layer.git
cd fact-knowledge-layer
```

Create a `.env` file in the project root:
```env
DATABASE_URL=postgresql+psycopg://postgres:factstuff@localhost:5432/factdb
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash
```

### 3. Start PostgreSQL with pgvector
```bash
docker compose up -d db
```
This spins up PostgreSQL 16 with the `pgvector` extension enabled on port `5432`.

### 4. Install Dependencies
```bash
# Optional: create a virtual environment
python -m venv .venv
.venv\Scripts\activate      # On Windows
# source .venv/bin/activate  # On macOS/Linux

pip install -r backend/requirements.txt
```

### 5. Run the FastAPI Server
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
*(Alternatively, you can run `python main.py` directly).*

Once the server is running:
- **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/api/health](http://localhost:8000/api/health)

### 6. Terminal CLI Mode (Alternative)
You can also run the pipeline directly from the command line:
```bash
python backend/main.py path/to/document.pdf
```

---

## Testing with Postman

A ready-to-use Postman Collection v2.1 is included at [`backend/postman_collection.json`](backend/postman_collection.json).

1. Open **Postman** and click **Import**.
2. Select [`backend/postman_collection.json`](backend/postman_collection.json).
3. The collection provides pre-configured requests:
   - `GET /api/health` — Verify system and database connectivity.
   - `POST /api/documents/upload` — Upload PDF (`multipart/form-data`) with asynchronous background processing.
   - `GET /api/documents` — Track document processing status and fact counts.
   - `GET /api/facts` — Query facts with search filters (entity, attribute, keyword) and source evidence.
   - `GET /api/relationships` — Inspect cross-document relationships (`corroborates`, `contradicts`, `context_explained`).
   - `GET /api/showcase` — Directly inspect the Four Required Cases.

---

## REST API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/documents/upload` | Upload PDF file (multipart/form-data). Supports async background task. |
| `GET` | `/api/documents` | List all ingested documents with status, page counts, and fact counts. |
| `GET` | `/api/documents/{id}` | Get document details and processing status. |
| `DELETE`| `/api/documents/{id}` | Cascade delete document, chunks, facts, and linked relationships. |
| `POST` | `/api/documents/reset` | Completely resets knowledge layer (deletes all docs, chunks, facts, and links). |
| `POST` | `/api/documents/{id}/reprocess` | Re-run extraction and comparison for an existing document. |
| `GET` | `/api/facts` | Query/search grounded facts (filters: `document_id`, `entity`, `attribute`, `search`). |
| `GET` | `/api/facts/{id}` | Retrieve a specific fact by ID with grounded quote and chunk. |
| `GET` | `/api/relationships` | List cross-document relationships (filter by `relationship_type` or `document_id`). |
| `GET` | `/api/relationships/{id}` | Retrieve comparative details of a specific relationship pair. |
| `POST` | `/api/relationships/compare` | Trigger cross-document comparison across completed documents. |
| `GET` | `/api/showcase` | Returns the Four Required Assignment Cases. |
| `GET` | `/api/stats` | System overview counts (documents, chunks, facts, relationships by type). |
| `GET` | `/api/settings` | Inspect active LLM provider (Gemini / Groq) and available models. |
| `POST` | `/api/settings` | Dynamically switch active LLM provider, target model, or runtime API key. |
| `GET` | `/api/health` | Service and database readiness check. |

---

## Video Demo

- **Link**: *[Demo Video Link - Under 3 minutes](https://youtube.com/placeholder)*
- **Demo Contents**:
  1. PDF upload and asynchronous ingestion tracking via API / Swagger.
  2. Fact extraction walkthrough showing entity, value, time scope, qualifiers, and raw evidence grounding.
  3. Demonstration of **Case 1**: Cross-document corroboration.
  4. Demonstration of **Case 2**: Genuine contradiction.
  5. Demonstration of **Case 3**: Apparent contradiction explained by context (Standalone vs Consolidated / Temporal differences).
  6. Demonstration of **Case 4**: Extraction/reasoning failure diagnostic and handling.

---

## Approach & Engineering Decisions

### 1. Document Ingestion & Page Normalization
- **2-Up Logical Page Splitting**: Prospectuses and annual reports are frequently exported in 2-up spread formats (two logical document pages rendered side-by-side on a single physical PDF page). A naive bounding box extraction causes text lines from the left and right pages to interleave. Our `page_normalizer.py` inspects block coordinates and aspect ratios to split 2-up spreads into independent logical pages.
- **Layout-Aware Chunking**: Rather than arbitrary character-based splitting, text blocks with bounding boxes are accumulated into cohesive chunks (~200 to 1,500 characters), preventing mid-sentence ruptures of financial tables.

### 2. Heuristic Pre-Filtering
- Sending every document chunk to an LLM quickly exhausts API rate limits and adds unnecessary latency.
- `filter.py` applies high-precision regex matching (currencies, percentages, quantitative metrics, corporate governance signals like appointments and acquisitions). Non-factual narrative chunks (disclaimers, instructions, boilerplate) are pruned locally, **cutting LLM calls by ~50%**.

### 3. Batch Structured Fact Extraction
- To respect free-tier rate limits and maximize throughput, chunks are grouped into batches of 5 per Gemini call (`extract_facts_batch`).
- Facts are strictly typed with canonicalized entity names, attributes, values, units, time scopes, and **qualifiers** (e.g. `basis: standalone` vs `consolidated`, `nature: audited` vs `unaudited`).
- Every fact preserves `raw_text` as verbatim source evidence for grounding.

### 4. Hybrid Candidate Retrieval & Structural Reranking
A naive all-pairs comparison between $N$ facts in Document A and $M$ facts in Document B scales quadratically ($O(N \times M)$). To make cross-document reasoning efficient:
1. **Vector Search via pgvector**: Facts are transformed into prose sentences and embedded via `gemini-embedding-001`. A cosine similarity threshold filters candidate matches.
2. **Structural Reranking**: Candidate pairs are scored via a hybrid blend:
   $$\text{Candidate Score} = 0.60 \times \text{Vector Similarity} + 0.40 \times \text{Structural Alignment}$$
   where structural alignment scores entity overlap, attribute token similarity, time compatibility, and unit compatibility.
3. **LLM Comparison Engine**: Only high-scoring candidate pairs are presented to Gemini for semantic classification: `corroborates`, `contradicts`, `context_explained`, or `unrelated`.

---

## Show Us These Four Cases

The system specifically targets and demonstrates the four cases required by the assignment:

### Case 1: Fact Corroborated Across Documents
- **Claim**: Corporate Registered Office of Delhivery Limited.
- **Document 1 (Prospectus 2022)**:
  - *Evidence*: `"Registered Office: N24-N34, S24-S34, Air Cargo Logistics Centre-II, Opposite Gate 6, Cargo Terminal, IGI Airport, New Delhi 110 037, India."`
- **Document 2 (Annual Report FY24)**:
  - *Evidence*: `"Corporate Office / Registered Office: Air Cargo Logistics Centre-II, Opp Gate 6, Cargo Terminal, IGI Airport, New Delhi - 110037."`
- **System Reasoning**: Both documents corroborate the identical corporate registered facility at IGI Airport New Delhi 110037 despite slight syntactic variations in suite numbering and punctuation. Classified as `corroborates`.

### Case 2: Genuine or Likely Contradiction
- **Claim**: Active PIN Code Coverage / Volume Statistics for an identical historical period.
- **Document 1 (Preliminary Prospectus Excerpt)**:
  - *Value*: `17,000+ PIN codes covered as of Dec 31, 2021`
- **Document 2 (Investor Presentation / Subsequent Filing)**:
  - *Value*: `16,400 PIN codes covered as of Dec 31, 2021`
- **System Reasoning**: Both documents report active PIN code coverage for the identical entity on the exact same reporting date, but provide materially conflicting numbers without reconciliation or restatement notes. Classified as `contradicts`.

### Case 3: Apparent Contradiction Explained by Context
- **Claim**: Delhivery Revenue from Operations for Fiscal Year 2024.
- **Fact A (Standalone Financials)**:
  - *Value*: `₹74,540.82 Million`
  - *Qualifiers*: `basis: standalone`, `time_scope: FY2023-24`
  - *Evidence*: `"Revenue from operations for the year ended March 31, 2024 stood at ₹ 74,540.82 million on a standalone basis."`
- **Fact B (Consolidated Financials)**:
  - *Value*: `₹81,424.87 Million`
  - *Qualifiers*: `basis: consolidated`, `time_scope: FY2023-24`
  - *Evidence*: `"Consolidated revenue from operations increased to ₹ 81,424.87 million for FY 2024."`
- **System Reasoning**: Although both facts describe Delhivery's FY24 operating revenue, the reasoning engine recognizes the reporting basis qualifier: ₹74,540.82M reflects Standalone company operations, whereas ₹81,424.87M reflects Consolidated group revenue including subsidiaries. Reconciled and classified as `context_explained`.

### Case 4: Extraction or Reasoning Failure Analysis & Improvement
- **Failure Identified**: Column header misattribution in multi-year financial tables.
- **Root Cause**: In multi-year balance sheets or income statements, stacked column headers (e.g. `FY24 Audited` vs `FY23 Audited` spanning `Standalone` vs `Consolidated`) are extracted by standard text-block extractors in linear top-to-bottom sequence. If text blocks interleave, numerical values in lower rows can become detached from their corresponding fiscal year column.
- **How We Handled It**:
  1. *Qualifier Extraction*: System prompt forces the LLM to extract explicit reporting qualifiers and time scopes rather than inferring them implicitly.
  2. *Confidence Scoring*: Low-confidence extractions where header alignment is ambiguous are scored with `confidence < 0.70`.
  3. *In-Document Deduplication*: Duplicate claims with conflicting scopes are filtered by keeping highest-confidence verified facts.
- **Proposed Future Improvement**: Implement coordinate-based table cell reconstruction using PDF vector drawing paths or pass raster image crops of tabular regions directly to multimodal vision models (e.g. Gemini 3.5 Flash Vision).

---

## Limitations and Next Steps

1. **Complex Table Geometries**: Unbordered financial tables with multi-tier nested headers are extracted as text rather than structured HTML/grid tables. Future iterations will incorporate raster table detection with OCR bounding-grid alignment.
2. **Interactive UI**: While the complete REST API and Swagger UI are fully operational, a dedicated React/Vite frontend dashboard with interactive graph visualization of cross-document links would enhance manual exploration.
3. **Multimodal Extraction**: Charts, infographics, and pie graphs inside annual reports currently cannot be parsed via PyMuPDF text extraction alone; integration with a vision API would unlock graphic facts.

---

## Additional Notes & Brownie Points

- **Incremental Knowledge Growth**: The system does not need to re-index all previous documents when a new document is uploaded. It extracts facts solely from the new document, embeds them, and queries the vector index to compare only against existing facts.
- **Domain-Agnostic Design**: Prompts and heuristic filters avoid hardcoded corporate names (e.g. "Delhivery") or document-specific schemas, ensuring the pipeline generalizes to healthcare, legal, or macroeconomic document corpora.
- **Safe Cascading**: Full deletion support ensures clean test cycles without orphan vector records.
