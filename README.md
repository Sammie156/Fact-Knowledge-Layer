# Fact Knowledge Layer

A prototype system that extracts factual claims from PDF documents,
grounds each fact in its source evidence, and compares facts across
documents to identify corroboration, contradiction, or contextual
differences.

## Current Status

🚧 Work in progress

Currently implemented:

- PDF ingestion using PyMuPDF
- Logical-page normalization for 2-up PDFs
- Layout-aware text block extraction
- Semantic-ish chunking of extracted content
- Structured fact extraction using Gemini
- Source evidence captured with each extracted fact

Planned:

- Persist extracted facts in PostgreSQL
- Generate fact embeddings
- Cross-document fact retrieval using pgvector
- Relationship reasoning between facts
- FastAPI API
- React UI
- Improved table extraction

---

## Architecture

Current pipeline:

PDF
↓
PyMuPDF
↓
Logical Page Normalization
↓
Text Blocks
↓
Chunks
↓
Gemini Fact Extraction
↓
Structured Facts

Planned:

Structured Facts
↓
Embeddings
↓
Vector Similarity Search
↓
Candidate Fact Pairs
↓
Gemini Relationship Reasoning
↓
Corroborates / Contradicts / Context Explained

---

## Tech Stack

- Python
- FastAPI
- PostgreSQL
- pgvector
- SQLAlchemy
- PyMuPDF
- Gemini API
- React (planned)

---

## PDF Processing

### PyMuPDF

PyMuPDF is used for PDF text extraction and page-level layout
information.

The ingestion layer first normalizes physical PDF pages into logical
pages. This is useful for documents that contain two logical pages
side-by-side on a single physical PDF page.

Each extracted logical page currently retains:

- physical page number
- logical page index
- region
- bounding box
- extracted text
- text blocks

### Tables

PyMuPDF's table detection was tested on the provided annual report.

The table detector was able to identify a region, but extraction of
the complete table was unreliable for some layouts.

For the current prototype, table content is therefore preserved as
text rather than fully normalized into structured cells.

A coordinate-based table reconstruction approach is planned as a
future improvement.

---

## Chunking

The current chunker uses extracted text blocks rather than blindly
splitting documents by character count.

Consecutive blocks are accumulated into chunks while attempting to
preserve useful context.

The current implementation intentionally favors preserving complete
document regions over enforcing a strict character limit.

---

## Fact Extraction

Gemini is currently used to extract structured facts from each chunk.

A fact contains:

- entity
- attribute
- value
- unit
- time scope
- qualifiers
- raw source text
- confidence

Example:

```json
{
  "entity": "Company",
  "attribute": "standalone revenue from operations",
  "value": "74,540.82",
  "unit": "INR million",
  "time_scope": "FY24",
  "qualifiers": [
    {
      "key": "basis",
      "value": "standalone"
    }
  ],
  "confidence": 1.0
}
