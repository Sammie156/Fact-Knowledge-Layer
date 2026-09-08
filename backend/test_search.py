from core.database import SessionLocal
from core.models import Fact

from facts.search import find_similar_facts


db = SessionLocal()

try:
    fact = (
        db.query(Fact)
        .filter(
            Fact.embedding.is_not(None),
            Fact.document_id != (
                db.query(Fact.document_id)
                .filter(Fact.embedding.is_not(None))
                .first()[0]
            ),
        )
        .first()
    )

    if fact is None:
        raise RuntimeError("No suitable fact found")

    print("QUERY FACT")
    print("----------------")
    print(f"Entity     : {fact.entity}")
    print(f"Attribute  : {fact.attribute}")
    print(f"Value      : {fact.value}")
    print(f"Unit       : {fact.unit}")
    print(f"Time scope : {fact.time_scope}")
    print()

    results = find_similar_facts(
        db=db,
        fact=fact,
        limit=5,
    )

    print("SIMILAR FACTS")
    print("----------------")

    for similar_fact, distance in results:
        print(
            f"Distance: {distance:.4f}"
        )
        print(
            f"  {similar_fact.entity} | "
            f"{similar_fact.attribute} | "
            f"{similar_fact.value} "
            f"{similar_fact.unit or ''} | "
            f"{similar_fact.time_scope or ''}"
        )
        print(
            f"  Evidence: {similar_fact.raw_text}"
        )
        print()

finally:
    db.close()