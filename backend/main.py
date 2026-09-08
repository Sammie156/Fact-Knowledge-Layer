import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from core.database import Base, engine, SessionLocal
from core.models import Document, Chunk
from ingestion.pdf_extractor import extract_pdf
from ingestion.chunker import chunk_page
from facts.pipeline import process_document
from facts.reasoner import run_comparison_for_document

from api.routes import documents, facts, relationships, showcase, stats, settings, graph


from sqlalchemy import text


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure database tables, schema migrations, and vector extensions are created on startup."""
    try:
        Base.metadata.create_all(bind=engine)
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS error_message TEXT;"))
            conn.execute(text("ALTER TABLE documents ALTER COLUMN status TYPE VARCHAR(50);"))
        print("[Startup] Database tables and schema verified.")
    except Exception as exc:
        print(f"[Startup Warning] Schema verification note: {exc}")
    yield


app = FastAPI(
    title="Fact Knowledge Layer API",
    description=(
        "AI-powered system that extracts factual claims from PDF documents, "
        "grounds each fact in verified source evidence, and discovers cross-document "
        "corroborations, contradictions, and context-explained reconciliations."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for browser testing, Postman, and frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(documents.router, prefix="/api")
app.include_router(facts.router, prefix="/api")
app.include_router(relationships.router, prefix="/api")
app.include_router(showcase.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(graph.router, prefix="/api")

# Mount Frontend UI (served at root '/')
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
else:
    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse(url="/docs")


# ----------------------------------------------------------------------
# CLI Fallback (Preserving terminal script functionality)
# ----------------------------------------------------------------------

def ingest_pdf_cli(db, pdf_path: str) -> tuple[Document, bool]:
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    existing = db.query(Document).filter(Document.filename == path.name).first()
    if existing:
        print(f"Found existing document: {existing.id} (status: {existing.status})")
        return existing, False

    print(f"Opening PDF: {path}")
    pages = extract_pdf(str(path))
    print(f"Extracted {len(pages)} logical pages")

    document = Document(
        filename=path.name,
        page_count=len(pages),
        status="processing",
    )
    db.add(document)
    db.flush()

    total_chunks = 0
    for page in pages:
        chunks = chunk_page(page)
        for chunk_data in chunks:
            chunk = Chunk(
                document_id=document.id,
                page_number=page.logical_page_index + 1,
                chunk_index=chunk_data.chunk_index,
                content=chunk_data.content,
                chunk_type=chunk_data.chunk_type,
                has_facts=False,
            )
            db.add(chunk)
            total_chunks += 1

    db.commit()
    print(f"Created document  : {document.id}")
    print(f"Created chunks    : {total_chunks}")
    return document, True


def run_cli():
    print("FACT KNOWLEDGE LAYER - CLI MODE")
    if len(sys.argv) < 2:
        print("Usage: python main.py <path-to-pdf>")
        print("Or run the API server: uvicorn main:app --reload")
        sys.exit(1)

    db = SessionLocal()
    try:
        document, is_new = ingest_pdf_cli(db, sys.argv[1])
        if document.status == "done":
            print("Document already fully processed. Running comparison only.")
            run_comparison_for_document(db=db, document_id=document.id)
            return

        print("\n" + "=" * 50)
        print("FACT EXTRACTION")
        print("=" * 50)
        total_facts = process_document(db=db, document_id=document.id)

        print("\n" + "=" * 50)
        print("CROSS-DOCUMENT COMPARISON")
        print("=" * 50)
        total_relationships = run_comparison_for_document(db=db, document_id=document.id)

        print("\n" + "=" * 50)
        print("PIPELINE COMPLETE")
        print("=" * 50)
        print(f"Document      : {document.filename}")
        print(f"Facts saved   : {total_facts}")
        print(f"Relationships : {total_relationships}")
    finally:
        db.close()


if __name__ == "__main__":
    # If a PDF file path is given as argument, run CLI; otherwise launch server
    if len(sys.argv) > 1 and sys.argv[1].endswith(".pdf"):
        run_cli()
    else:
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)