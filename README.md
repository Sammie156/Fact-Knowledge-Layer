# Fact Knowledge Layer

An AI-powered system that extracts structured factual claims from unstructured PDF documents, grounds every fact in verifiable source evidence (page number and exact verbatim quote), and discovers cross-document relationships—identifying **corroborations**, **genuine contradictions**, and **apparent contradictions reconciled by context** (such as differences in time scopes, reporting bases, or units).

Includes a modern **Web UI Dashboard**, an **Obsidian-inspired Interactive Knowledge Graph**, a **Multi-LLM Switcher** (Gemini & Groq), and a complete **FastAPI REST API**.

---

## Quickstart (The Simplest Way - 2 Steps with Docker)

> **No complex setup needed.** If you have Docker installed, the entire system—including **PostgreSQL with pgvector**, database migrations, API backend, and the interactive frontend dashboard—starts with a single command.

### 1. Clone the repository and configure your API key

```bash
git clone https://github.com/Sammie156/Fact-Knowledge-Layer.git
cd Fact-Knowledge-Layer

# Copy the environment template
cp .env.example .env
```

Open `.env` and paste your free **Google Gemini API Key** ([get one here in 30 seconds](https://aistudio.google.com/)):

```env
GEMINI_API_KEY=AIzaSyYourKeyHere
```

### 2. Start the entire application

```bash
docker compose up --build
```

**That's it!** Once the containers start, open your browser:

- 🌐 **Web Dashboard & Interactive Graph**: [http://localhost:8000](http://localhost:8000)
- 📚 **Interactive Swagger API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- 🩺 **Health Check**: [http://localhost:8000/api/health](http://localhost:8000/api/health)

To stop the application at any time, press `Ctrl+C` or run:

```bash
docker compose down
```

_(Uploaded documents and database vector records are safely persisted in Docker volumes across restarts)._

---

## 🌐 Features & Web Dashboard

- **Obsidian-Style Knowledge Graph**: Real-time visual network of connected facts across documents, color-coded by relationship type (green for corroborates, red for contradicts, amber for context-explained).
- **Drag-and-Drop PDF Ingestion**: Upload dense annual reports or prospectuses directly from the browser with live background progress tracking.
- **Fact & Relationship Explorer**: Search, filter, and inspect grounded source citations and confidence scores.
- **Live LLM Switcher (Settings ⚙️)**: Seamlessly switch between **Google Gemini 3.5 Flash** and **Groq Llama-3.3-70B**, test API latency, or set keys on-the-fly directly in the UI.
- **Circuit Breaker**: Automatic failover to Groq if Gemini hits rate limits during heavy document processing.

---

## 🚀 Deploying to Cloud / Production

The application is fully containerized and can be deployed anywhere Docker is supported.

### Option A: Deploy to any VPS (DigitalOcean Droplet, AWS EC2, Hetzner, Linode)

1. SSH into your server and install Docker & Docker Compose:
   ```bash
   sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin
   ```
2. Clone the repository and configure `.env`:
   ```bash
   git clone https://github.com/Sammie156/Fact-Knowledge-Layer.git
   cd Fact-Knowledge-Layer
   cp .env.example .env
   nano .env  # Add GEMINI_API_KEY
   ```
3. Launch with Docker Compose in detached mode:
   ```bash
   docker compose up -d --build
   ```
   Your application will be live at `http://<your-server-ip>:8000`.

---

### Option B: Deploy to PaaS (Render, Railway, Fly.io)

The repository includes a production-ready root [`Dockerfile`](Dockerfile) that bundles the FastAPI backend, background workers, and static frontend into a single container.

1. **Database**: Provision a PostgreSQL database with the `pgvector` extension enabled (available natively on [Neon](https://neon.tech/), [Supabase](https://supabase.com/), or Railway Postgres).
2. **Environment Variables**:
   - `DATABASE_URL`: Your cloud PostgreSQL connection string (`postgresql+psycopg://user:pass@host:5432/dbname`)
   - `GEMINI_API_KEY`: Your Google Gemini API key
   - `LLM_PROVIDER`: `gemini` (or `groq`)
3. **Deploy Container**: Point your cloud provider to the repository's root `Dockerfile` and expose port `8000`.

---

## Alternative Setup (Local Python Development)

If you prefer developing locally outside Docker, follow these steps:

### 1. Prerequisites

- **Python**: 3.11 or 3.12
- **Docker**: For running PostgreSQL with `pgvector`
- **Google Gemini API Key**: [Get key here](https://aistudio.google.com/)

### 2. Start PostgreSQL with pgvector

```bash
docker compose up -d db
```

This spins up PostgreSQL 16 with `pgvector` on port `5432`.

### 3. Install Python Dependencies

```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate      # On Windows
# source .venv/bin/activate  # On macOS/Linux

pip install -r backend/requirements.txt
```

### 4. Configure `.env`

Create `.env` in the project root:

```env
DATABASE_URL=postgresql+psycopg://postgres:factstuff@localhost:5432/factdb
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash
```

### 5. Run the Application

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open [http://localhost:8000](http://localhost:8000) to access the Web UI and API.

---

## 🏗️ Architecture & Pipeline

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
       (Minimizes chunks: up to ~4,500 chars)
                       │
                       ▼
        Regex Fact-Bearing Pre-Filter
        (Prunes ~50% of non-fact chunks)
                       │
                       ▼
        Structured LLM Fact Extraction
         (Batch size: 3 chunks per call)
         - Entity (Canonicalized)
         - Attribute & Value
         - Time Scope & Unit
         - Context Qualifiers (Standalone/Consolidated)
         - Raw Verbatim Evidence Quote
                       │
                       ▼
       PostgreSQL + pgvector Fact Storage
            (Deduplication & Storage)
                       │
                       ▼
          Batch Fact Vector Embeddings
             (gemini-embedding-001)
                       │
                       ▼
            Candidate Similarity Search
     (pgvector Cosine Distance >= 0.75 + Reranking)
                       │
                       ▼
        LLM Comparative Reasoning Engine
   ┌───────────────────┼───────────────────┐
   ▼                   ▼                   ▼
Corroborates     Contradicts     Context-Explained
```

---

## 🧪 Testing with Postman

A pre-configured Postman Collection v2.1 is included at [`backend/postman_collection.json`](backend/postman_collection.json).

1. Open **Postman** and click **Import**.
2. Select [`backend/postman_collection.json`](backend/postman_collection.json).
3. The collection includes ready-to-test endpoints:
   - `GET /api/health` — System and database readiness check.
   - `POST /api/documents/upload` — Upload PDF with asynchronous background extraction.
   - `GET /api/documents` — Track document processing status and fact counts.
   - `GET /api/facts` — Query facts with filters (entity, attribute, keyword search).
   - `GET /api/relationships` — Filter cross-document links (`corroborates`, `contradicts`, `context_explained`).
   - `GET /api/graph` — Graph nodes and links for visualization.

---

## 📋 REST API Reference

| Method   | Endpoint                        | Description                                                                            |
| :------- | :------------------------------ | :------------------------------------------------------------------------------------- |
| `POST`   | `/api/documents/upload`         | Upload PDF file (multipart/form-data). Supports async background task.                 |
| `GET`    | `/api/documents`                | List all ingested documents with status, page counts, and fact counts.                 |
| `GET`    | `/api/documents/{id}`           | Get document details and processing status.                                            |
| `DELETE` | `/api/documents/{id}`           | Cascade delete document, chunks, facts, and linked relationships.                      |
| `POST`   | `/api/documents/reset`          | Completely resets knowledge layer (deletes all docs, chunks, facts, and links).        |
| `POST`   | `/api/documents/{id}/reprocess` | Re-run extraction and comparison for an existing document.                             |
| `GET`    | `/api/facts`                    | Query/search grounded facts (filters: `document_id`, `entity`, `attribute`, `search`). |
| `GET`    | `/api/facts/{id}`               | Retrieve a specific fact by ID with grounded quote and chunk metadata.                 |
| `GET`    | `/api/relationships`            | List cross-document relationships (filter by `relationship_type` or `document_id`).    |
| `GET`    | `/api/relationships/{id}`       | Retrieve comparative details of a specific relationship pair.                          |
| `POST`   | `/api/relationships/compare`    | Trigger cross-document comparison across completed documents.                          |
| `GET`    | `/api/graph`                    | Graph nodes and links formatted for force-directed knowledge graph visualization.      |
| `GET`    | `/api/stats`                    | System overview counts (documents, chunks, facts, relationships by type).              |
| `GET`    | `/api/settings`                 | Inspect active LLM provider (Gemini / Groq) and live available models.                 |
| `POST`   | `/api/settings`                 | Dynamically switch active LLM provider, target model, or runtime API key.              |
| `GET`    | `/api/health`                   | Service and database readiness check.                                                  |

---

## ⚙️ Engineering Decisions & Rate Limit Optimization

1. **Chunk Minimization for Dense PDFs**: Dense PDFs (tables, columns) previously produced hundreds of micro-chunks. We set `MAX_CHUNK_CHARS = 4500` and `MIN_CHUNK_CHARS = 600`, merging small trailing residual blocks into previous chunks. A 100-page dense prospectus now produces only **~102 cohesive chunks** (70% reduction).
2. **Batch Fact Embeddings**: Replaced sequential 1-by-1 embedding API calls with native batch embeddings (`contents=[...]`), embedding up to 50 facts per API call (**98% reduction in network round-trips**).
3. **15 RPM Free-Tier Rate Limiting Safety**: Fact extraction batches use a 3.5-second buffer and relationship reasoning applies a 2.0-second candidate throttle with adaptive cooldown backoff on 429 errors.
4. **Heuristic Pre-Filtering**: Non-factual narrative chunks (disclaimers, table of contents, legal boilerplate) are pruned locally via high-precision regex before calling the LLM, cutting extraction calls by ~50%.
5. **Zero-Setup Database Initialization**: On container boot, the database lifespan automatically creates the `vector` extension and all tables without requiring manual migration scripts.
