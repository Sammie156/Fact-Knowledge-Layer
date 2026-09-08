from core.database import SessionLocal
from core.models import Document

from facts.embed_pipeline import embed_document_facts


DOCUMENT_FILENAME = "03-delhivery-q4-fy24-earnings-presentation.pdf"


db = SessionLocal()

try:
    document = (
        db.query(Document)
        .filter(Document.filename == DOCUMENT_FILENAME)
        .first()
    )

    if document is None:
        raise RuntimeError(
            f"Document not found: {DOCUMENT_FILENAME}"
        )

    count = embed_document_facts(
        db=db,
        document_id=document.id,
    )

    print(f"\nEmbedded {count} facts.")

finally:
    db.close()