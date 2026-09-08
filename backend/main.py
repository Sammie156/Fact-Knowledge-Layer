import sys
from pathlib import Path

from core.database import SessionLocal
from core.models import Document, Chunk

from ingestion.pdf_extractor import extract_pdf
from ingestion.chunker import chunk_page

from facts.pipeline import process_document
from facts.reasoner import run_comparison_for_document


def ingest_pdf(db, pdf_path: str) -> tuple[Document, bool]:
    """
    Returns (document, is_new).
    If a document with this filename already exists, returns it as-is.
    """
    path = Path(pdf_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    # Check if already ingested
    existing = db.query(Document).filter(
        Document.filename == path.name
    ).first()

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


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <path-to-pdf>")
        sys.exit(1)

    db = SessionLocal()

    try:
        document, is_new = ingest_pdf(db, sys.argv[1])

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

        total_relationships = run_comparison_for_document(
            db=db, document_id=document.id
        )

        print("\n" + "=" * 50)
        print("PIPELINE COMPLETE")
        print("=" * 50)
        print(f"Document      : {document.filename}")
        print(f"Facts saved   : {total_facts}")
        print(f"Relationships : {total_relationships}")

    finally:
        db.close()