from sqlalchemy.orm import Session

from core.models import Fact
from facts.schemas import FactExtractionResult


def save_facts(
    db: Session,
    document_id,
    chunk_id,
    page_number: int,
    result: FactExtractionResult,
) -> list[Fact]:

    facts = []

    for extracted_fact in result.facts:
        fact = Fact(
            document_id=document_id,
            chunk_id=chunk_id,
            entity=extracted_fact.entity,
            attribute=extracted_fact.attribute,
            value=extracted_fact.value,
            unit=extracted_fact.unit,
            time_scope=extracted_fact.time_scope,
            qualifiers=[
                {
                    "key": qualifier.key,
                    "value": qualifier.value,
                }
                for qualifier in extracted_fact.qualifiers
            ],
            raw_text=extracted_fact.raw_text,
            page_number=page_number,
            confidence=extracted_fact.confidence,
        )

        db.add(fact)
        facts.append(fact)

    db.commit()

    return facts