from sqlalchemy.orm import Session

from core.models import Fact
from facts.matcher import candidate_score


SIMILARITY_THRESHOLD = 0.75


def find_similar_facts(
    db: Session,
    fact: Fact,
    limit: int = 10,
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[tuple[Fact, float]]:
    """
    Find facts from other documents that are semantically similar to `fact`.

    Retrieves vector similarity candidates via pgvector and reranks them
    using domain-agnostic structural scoring (combining entity, attribute,
    time, and unit alignment).
    """
    if fact.embedding is None:
        return []

    distance = Fact.embedding.cosine_distance(fact.embedding)
    similarity = (1 - distance).label("similarity")

    fetch_limit = limit * 3

    results = (
        db.query(Fact, similarity)
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

    scored = [
        (candidate, candidate_score(fact, candidate, float(vsim)))
        for candidate, vsim in results
    ]

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]