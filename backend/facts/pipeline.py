import time

from sqlalchemy.orm import Session

from core.models import Document, Chunk
from facts.filter import looks_fact_bearing
from facts.gemini_client import extract_facts_batch
from facts.repository import save_facts
from facts.schemas import FactExtractionResult
from facts.embed_pipeline import deduplicate_facts, embed_document_facts


# Number of chunks sent to Gemini in a single API call.
# 5 is a safe default — large enough to cut calls by 5x,
# small enough that the prompt stays well within context limits
# even for dense financial table chunks.
BATCH_SIZE = 5

# Seconds to sleep between batch calls to stay within free tier
# rate limits (15 RPM for flash models).
# At BATCH_SIZE=5 and 1.5s sleep: ~20 calls/min for a 150-chunk doc.
BATCH_SLEEP = 1.5


def process_document(
    db: Session,
    document_id,
) -> int:
    """
    Full fact extraction pipeline for a single document.

    Steps:
      1. Filter chunks by local heuristic — no Gemini call, cuts ~50%.
      2. Send fact-bearing chunks to Gemini in batches of BATCH_SIZE.
      3. Save facts, attributed to their source chunk.
      4. Deduplicate within the document.
      5. Embed all facts.

    Returns the total number of facts saved after deduplication.
    """
    document = db.get(Document, document_id)

    if document is None:
        raise ValueError(f"Document not found: {document_id}")

    chunks = (
        db.query(Chunk)
        .filter(Chunk.document_id == document_id)
        .order_by(Chunk.page_number, Chunk.chunk_index)
        .all()
    )

    # ------------------------------------------------------------------
    # Step 1: Local filter
    # ------------------------------------------------------------------

    candidates = [
        c for c in chunks
        if looks_fact_bearing(c.content) and not c.has_facts
    ]

    skipped = len(chunks) - len(candidates)

    print(f"Total chunks     : {len(chunks)}")
    print(f"Skipped by filter: {skipped}")
    print(f"Sending to Gemini: {len(candidates)}")
    print(f"Batches          : {-(-len(candidates) // BATCH_SIZE)}")  # ceil div

    total_facts = 0

    # ------------------------------------------------------------------
    # Step 2 + 3: Batch extraction and save
    # ------------------------------------------------------------------

    for batch_start in range(0, len(candidates), BATCH_SIZE):
        batch = candidates[batch_start: batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        total_batches = -(-len(candidates) // BATCH_SIZE)

        print(
            f"\nBatch [{batch_num}/{total_batches}] — "
            f"{len(batch)} chunks "
            f"(pages {batch[0].page_number}–{batch[-1].page_number})"
        )

        # Build indexed list for the prompt: (position_in_batch, content)
        indexed = [(i, chunk.content) for i, chunk in enumerate(batch)]

        try:
            result = extract_facts_batch(indexed)

            for chunk_result in result.chunks:
                # Guard against Gemini returning an out-of-range index
                if chunk_result.chunk_index >= len(batch):
                    print(
                        f"  Warning: chunk_index {chunk_result.chunk_index} "
                        f"out of range for batch of {len(batch)}, skipping"
                    )
                    continue

                chunk = batch[chunk_result.chunk_index]

                if not chunk_result.facts:
                    print(
                        f"  chunk {chunk_result.chunk_index} "
                        f"(page {chunk.page_number}) → no facts"
                    )
                    continue

                # Wrap as FactExtractionResult for save_facts compatibility
                wrapped = FactExtractionResult(facts=chunk_result.facts)

                save_facts(
                    db=db,
                    document_id=document.id,
                    chunk_id=chunk.id,
                    page_number=chunk.page_number,
                    result=wrapped,
                )

                chunk.has_facts = True
                total_facts += len(chunk_result.facts)

                print(
                    f"  chunk {chunk_result.chunk_index} "
                    f"(page {chunk.page_number}) "
                    f"→ {len(chunk_result.facts)} facts"
                )

            db.commit()

        except Exception as exc:
            print(f"  Batch {batch_num} FAILED: {exc}")
            continue

        # Rate limit buffer between batches
        if batch_start + BATCH_SIZE < len(candidates):
            time.sleep(BATCH_SLEEP)

    # ------------------------------------------------------------------
    # Step 4: Deduplicate
    # ------------------------------------------------------------------

    print(f"\nDeduplicating...")
    removed = deduplicate_facts(db, document_id)
    if removed:
        print(f"Removed {removed} duplicate facts.")
        total_facts -= removed

    # ------------------------------------------------------------------
    # Step 5: Embed
    # ------------------------------------------------------------------

    print(f"\nEmbedding facts...")
    embedded = embed_document_facts(db, document_id)
    print(f"Embedded {embedded} facts.")

    document.status = "done"
    db.commit()

    return total_facts
