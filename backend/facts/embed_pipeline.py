from sqlalchemy.orm import Session

from core.models import Fact
from facts.embeddings import build_fact_text, generate_embedding


def embed_document_facts(
    db: Session,
    document_id,
) -> int:

    facts = (
        db.query(Fact)
        .filter(
            Fact.document_id == document_id,
            Fact.embedding.is_(None),
        )
        .all()
    )

    embedded_count = 0

    for index, fact in enumerate(facts, start=1):

        print(
            f"[{index}/{len(facts)}] "
            f"Embedding: {fact.entity} | {fact.attribute}"
        )

        text = build_fact_text(
            entity=fact.entity,
            attribute=fact.attribute,
            value=fact.value,
            unit=fact.unit,
            time_scope=fact.time_scope,
            qualifiers=fact.qualifiers,
        )

        fact.embedding = generate_embedding(text)

        embedded_count += 1

    db.commit()

    return embedded_count