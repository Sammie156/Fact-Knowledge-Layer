from core.database import SessionLocal
from core.models import Document


with SessionLocal() as db:
    document = db.query(Document).first()

    print("Filename:", document.filename)
    print("Domain:", document.domain)
    print("Pages:", document.page_count)

    print("\nChunks:")

    for chunk in document.chunks:
        print(
            f"  Page {chunk.page_number}, "
            f"Chunk {chunk.chunk_index}: "
            f"{chunk.content}"
        )