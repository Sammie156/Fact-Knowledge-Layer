from core.database import SessionLocal
from core.models import Fact
from facts.search import find_similar_facts


db = SessionLocal()

try:
    # Pick any fact that has an embedding — search handles cross-doc filtering.
    fact = (
        db.query(Fact)
        .filter(Fact.embedding.is_not(None))
        .first()
    )

    if fact is None:
        raise RuntimeError(
            "No embedded facts found. "
            "Run embed_pipeline.py first."
        )

    print("QUERY FACT")
    print("-" * 40)
    print(f"Entity     : {fact.entity}")
    print(f"Attribute  : {fact.attribute}")
    print(f"Value      : {fact.value}")
    print(f"Unit       : {fact.unit}")
    print(f"Time scope : {fact.time_scope}")
    print(f"Document   : {fact.document.filename}")
    print()

    results = find_similar_facts(db=db, fact=fact, limit=5)

    if not results:
        print("No similar facts found above threshold.")
        print("Try lowering SIMILARITY_THRESHOLD in search.py")
    else:
        print("SIMILAR FACTS")
        print("-" * 40)

        for similar_fact, score in results:
            print(f"Combined score : {score:.4f}")
            print(
                f"  {similar_fact.entity} | "
                f"{similar_fact.attribute} | "
                f"{similar_fact.value} "
                f"{similar_fact.unit or ''} | "
                f"{similar_fact.time_scope or ''}"
            )
            print(f"  Document  : {similar_fact.document.filename}")
            print(f"  Evidence  : {similar_fact.raw_text}")
            print()

finally:
    db.close()
