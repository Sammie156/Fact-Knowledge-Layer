from sqlalchemy.orm import Session

from core.models import Fact


def find_similar_facts(
    db: Session,
    fact: Fact,
    limit: int = 5,
) -> list[tuple[Fact, float]]:

    distance = Fact.embedding.cosine_distance(
        fact.embedding
    ).label("distance")

    results = (
        db.query(Fact, distance)
        .filter(
            Fact.embedding.is_not(None),
            Fact.document_id != fact.document_id,
            Fact.id != fact.id,
        )
        .order_by(distance)
        .limit(limit)
        .all()
    )

    return [
        (result_fact, float(distance_value))
        for result_fact, distance_value in results
    ]