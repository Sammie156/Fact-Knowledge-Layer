from core.database import SessionLocal
from core.models import Document, Chunk
from facts.extractor import extract_facts
from facts.repository import save_facts


db = SessionLocal()

document = db.query(Document).first()

if document is None:
    raise RuntimeError("No document found")

chunk = db.query(Chunk).filter(
    Chunk.document_id == document.id
).first()

if chunk is None:
    raise RuntimeError("No chunk found")

result = extract_facts(chunk.content)

facts = save_facts(
    db=db,
    document_id=document.id,
    chunk_id=chunk.id,
    page_number=chunk.page_number,
    result=result,
)

print(f"Saved {len(facts)} facts")

for fact in facts:
    print(
        fact.entity,
        "|",
        fact.attribute,
        "|",
        fact.value,
        "|",
        fact.unit,
    )

db.close()