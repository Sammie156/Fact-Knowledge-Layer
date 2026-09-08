from sqlalchemy.orm import Session

from core.models import Fact


def find_similar_facts(
    db: Session,
    fact: Fact,
    limit: int = 20,
):
    distance = Fact.embedding.cosine_distance(fact.embedding)
    similarity = (1 - distance).label("similarity")

    results = (
        db.query(Fact, similarity)
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
        (candidate, float(vector_similarity))
        for candidate, vector_similarity in results
    ]