from sqlalchemy.orm import Session

from core.models import Fact
from facts.matcher import candidate_score


# Minimum vector similarity to be considered a candidate at all.
# Facts below this are almost certainly unrelated.
SIMILARITY_THRESHOLD = 0.78

# Minimum combined score (vector + structural) to be returned.
COMBINED_THRESHOLD = 0.70


def find_similar_facts(
    db: Session,
    fact: Fact,
    limit: int = 10,
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[tuple[Fact, float]]:
    """
    Find facts from other documents that are semantically similar to `fact`.

    Returns a list of (candidate_fact, combined_score) tuples sorted by
    combined score descending. The combined score weights vector similarity
    (60%) and structural similarity — entity, attribute, time, unit (40%).

    Only returns candidates from different documents.
    """
    if fact.embedding is None:
        return []

    distance = Fact.embedding.cosine_distance(fact.embedding)
    vector_sim = (1 - distance).label("vector_similarity")

    # Pull more candidates than needed so structural scoring can rerank.
    fetch_limit = limit * 3

    rows = (
        db.query(Fact, vector_sim)
        .filter(
            Fact.embedding.is_not(None),
            Fact.document_id != fact.document_id,
            Fact.id != fact.id,
            (1 - distance) >= threshold,
        )
        .order_by(distance)
        .limit(fetch_limit)
        .all()
    )

    # Rerank using combined vector + structural score.
    scored = [
        (candidate, candidate_score(fact, candidate, float(vsim)))
        for candidate, vsim in rows
    ]

    # Filter by combined threshold and sort by combined score.
    scored = [
        (candidate, score)
        for candidate, score in scored
        if score >= COMBINED_THRESHOLD
    ]

    scored.sort(key=lambda x: x[1], reverse=True)

    return scored[:limit]
