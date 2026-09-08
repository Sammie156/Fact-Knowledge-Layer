from sqlalchemy.orm import Session
from sqlalchemy import text

from core.models import Fact
from facts.embeddings import build_fact_text, generate_embedding


def deduplicate_facts(db: Session, document_id) -> int:
    """
    Remove duplicate facts within a document.

    Duplicates are defined as facts with the same entity, attribute,
    value, and time_scope. When duplicates exist, keep the one with
    the highest confidence score.

    Returns the number of rows deleted.
    """
    result = db.execute(text("""
        DELETE FROM facts
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY document_id, entity, attribute, value, time_scope
                           ORDER BY confidence DESC
                       ) AS rn
                FROM facts
                WHERE document_id = :doc_id
            ) ranked
            WHERE rn > 1
        )
    """), {"doc_id": str(document_id)})

    db.commit()
    return result.rowcount


def embed_document_facts(
    db: Session,
    document_id,
) -> int:
    """
    Generate and store embeddings for all un-embedded facts in a document.

    Skips facts that already have an embedding, so this is safe to call
    multiple times on the same document (e.g. after re-extraction).

    Returns the number of facts embedded.
    """
    facts = (
        db.query(Fact)
        .filter(
            Fact.document_id == document_id,
            Fact.embedding.is_(None),
        )
        .all()
    )

    if not facts:
        print("No un-embedded facts found.")
        return 0

    embedded_count = 0

    for index, fact in enumerate(facts, start=1):
        print(
            f"[{index}/{len(facts)}] "
            f"Embedding: {fact.entity} | {fact.attribute}"
        )

        text_to_embed = build_fact_text(
            entity=fact.entity,
            attribute=fact.attribute,
            value=fact.value,
            unit=fact.unit,
            time_scope=fact.time_scope,
            qualifiers=fact.qualifiers,
        )

        fact.embedding = generate_embedding(text_to_embed)
        embedded_count += 1

    db.commit()

    return embedded_count
