from sqlalchemy.orm import Session

from core.models import Document, Chunk
from facts.extractor import extract_facts
from facts.filter import looks_fact_bearing
from facts.repository import save_facts


def process_document(
    db: Session,
    document_id,
) -> int:

    document = db.get(Document, document_id)

    if document is None:
        raise ValueError(f"Document not found: {document_id}")

    chunks = (
        db.query(Chunk)
        .filter(Chunk.document_id == document_id)
        .order_by(Chunk.page_number, Chunk.chunk_index)
        .all()
    )

    total_facts = 0

    for index, chunk in enumerate(chunks, start=1):

        print(
            f"[{index}/{len(chunks)}] "
            f"Processing page {chunk.page_number}, "
            f"chunk {chunk.chunk_index}"
        )

        print(f"  content preview: {chunk.content[:300]!r}")

        if not looks_fact_bearing(chunk.content):
            print("  → skipped by local filter")
            continue

        try:
            result = extract_facts(chunk.content)

            if not result.facts:
                print("  → no facts found")
                continue

            facts = save_facts(
                db=db,
                document_id=document.id,
                chunk_id=chunk.id,
                page_number=chunk.page_number,
                result=result,
            )

            chunk.has_facts = True
            db.commit()

            total_facts += len(facts)

            print(f"  → saved {len(facts)} facts")

        except Exception as exc:
            print(
                f"  → FAILED: {exc}"
            )
            continue

    document.status = "processed"
    db.commit()

    return total_facts