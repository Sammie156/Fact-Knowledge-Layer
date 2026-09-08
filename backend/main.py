from pathlib import Path

from core.database import SessionLocal
from core.models import Document, Chunk

from ingestion.pdf_extractor import extract_pdf
from ingestion.chunker import chunk_page

from facts.pipeline import process_document


PDF_PATH = "C:/Users/saman/Downloads/02-delhivery-annual-report-fy24-excerpt.pdf"


def ingest_pdf(db, pdf_path: str) -> Document:
    path = Path(pdf_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

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

    print(f"Created document: {document.id}")
    print(f"Created {total_chunks} chunks")

    return document


def main():
    db = SessionLocal()

    try:
        # --------------------------------------------------
        # 1. PDF → Document + Chunks
        # --------------------------------------------------

        document = ingest_pdf(
            db,
            PDF_PATH,
        )

        # --------------------------------------------------
        # 2. Chunks → Gemini → Facts → PostgreSQL
        # --------------------------------------------------

        print("\nStarting fact extraction...\n")

        total_facts = process_document(
            db=db,
            document_id=document.id,
        )

        print("\n==============================")
        print("PIPELINE COMPLETE")
        print("==============================")
        print(f"Document : {document.filename}")
        print(f"Document ID: {document.id}")
        print(f"Facts saved: {total_facts}")

        # --------------------------------------------------
        # 3. Display saved facts
        # --------------------------------------------------

        facts = document.facts

        print("\nExtracted facts:\n")

        for fact in facts:
            print(
                f"[Page {fact.page_number}] "
                f"{fact.entity} | "
                f"{fact.attribute} | "
                f"{fact.value} "
                f"{fact.unit or ''} | "
                f"{fact.time_scope or ''}"
            )

            print(f"  Evidence: {fact.raw_text}")
            print(f"  Confidence: {fact.confidence}")
            print()

    finally:
        db.close()


if __name__ == "__main__":
    main()