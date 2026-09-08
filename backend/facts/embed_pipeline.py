from sqlalchemy.orm import Session
from sqlalchemy import text

from core.models import Fact
from facts.embeddings import (
    build_fact_text,
    generate_embedding,
    generate_embeddings_batch,
)


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


EMBED_BATCH_SIZE = 50


def embed_document_facts(
    db: Session,
    document_id,
) -> int:
    """
    Generate and store embeddings for all un-embedded facts in a document.
    Uses batch embedding to minimize API calls and eliminate 429 rate limit errors.

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
    total_facts = len(facts)

    for i in range(0, total_facts, EMBED_BATCH_SIZE):
        batch = facts[i : i + EMBED_BATCH_SIZE]
        batch_num = (i // EMBED_BATCH_SIZE) + 1
        total_batches = -(-total_facts // EMBED_BATCH_SIZE)

        print(
            f"[Embed Batch {batch_num}/{total_batches}] "
            f"Embedding facts {i + 1}–{i + len(batch)} of {total_facts}..."
        )

        texts_to_embed = [
            build_fact_text(
                entity=f.entity,
                attribute=f.attribute,
                value=f.value,
                unit=f.unit,
                time_scope=f.time_scope,
                qualifiers=f.qualifiers,
            )
            for f in batch
        ]

        try:
            embeddings = generate_embeddings_batch(texts_to_embed)
            for f, emb in zip(batch, embeddings):
                f.embedding = emb
            db.commit()
            embedded_count += len(batch)
        except Exception as exc:
            print(f"[Embed Batch {batch_num}] Batch embedding failed: {exc}, falling back to single...")
            for f, text_to_embed in zip(batch, texts_to_embed):
                try:
                    f.embedding = generate_embedding(text_to_embed)
                    embedded_count += 1
                except Exception as single_exc:
                    print(f"  → Single embedding failed for fact {f.id}: {single_exc}")
            db.commit()

    return embedded_count
