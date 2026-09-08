from sqlalchemy.orm import Session
from core.models import Fact


SIMILARITY_THRESHOLD = 0.80  # only return genuinely similar facts


def find_similar_facts(
    db: Session,
    fact: Fact,
    limit: int = 10,
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[tuple[Fact, float]]:

    if fact.embedding is None:
        return []

    distance = Fact.embedding.cosine_distance(fact.embedding)
    similarity = (1 - distance).label("similarity")

    results = (
        db.query(Fact, similarity)
        .filter(
            Fact.embedding.is_not(None),
            Fact.document_id != fact.document_id,
            Fact.id != fact.id,
            # only return facts above the threshold
            (1 - distance) >= threshold,
        )
        .order_by(distance)
        .limit(limit)
        .all()
    )

    return [
        (candidate, float(sim))
        for candidate, sim in results
    ]