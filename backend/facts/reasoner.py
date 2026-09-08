import time
from enum import Enum

from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.config import settings
from core.models import Fact, Relationship
from facts.search import find_similar_facts

client = genai.Client(api_key=settings.gemini_api_key)


class RelationshipType(str, Enum):
    CORROBORATES = "corroborates"
    CONTRADICTS = "contradicts"
    CONTEXT_EXPLAINED = "context_explained"
    UNRELATED = "unrelated"


class ComparisonResult(BaseModel):
    same_subject: bool
    relationship_type: RelationshipType
    explanation: str = Field(
        description=(
            "Clear explanation of why these facts corroborate, contradict, "
            "or appear to contradict but are explained by context. "
            "Reference specific values, time periods, and units."
        )
    )
    confidence: float = Field(ge=0.0, le=1.0)


COMPARISON_SYSTEM_PROMPT = """
You are a fact comparison system. You compare two facts extracted from
different documents and determine whether they corroborate, contradict,
or appear to contradict but can be explained by context.

Relationship types:
- corroborates: Both facts make the same or consistent claim.
  Values may differ slightly due to rounding. Time periods must be the same.
- contradicts: Both facts make genuinely conflicting claims about the
  same subject in the same time period with no contextual explanation.
- context_explained: Facts appear to conflict but the difference is
  explained by context — different time periods, different accounting
  bases (e.g., standalone vs consolidated), different reporting units or scales,
  different scopes/definitions, or one being a revision of a provisional figure.
- unrelated: Facts are about different subjects and cannot be meaningfully
  compared.

Rules:
- If time periods differ, classify as context_explained, not contradicts.
- If units or numerical scales differ (e.g., Millions vs Crores vs Billions,
  percentages vs basis points), check if values are mathematically consistent
  after conversion. If consistent, classify as corroborates. If not, classify
  as context_explained.
- Differences in scope or reporting basis (e.g., standalone vs consolidated,
  gross vs net, recurring vs one-off) for the same metric and period should
  be classified as context_explained, not contradicts.
- Be specific in your explanation — cite the actual values, units, and why
  they agree, conflict, or reconcile.
"""


def compare_facts(
    fact_a: Fact,
    fact_b: Fact,
    max_retries: int = 3,
) -> ComparisonResult:
    """
    Ask Gemini to compare two facts and classify their relationship.
    """

    def format_fact(fact: Fact, label: str) -> str:
        qualifier_str = ""
        if fact.qualifiers:
            q_parts = [f"{q['key']}: {q['value']}" for q in fact.qualifiers]
            qualifier_str = f"\n  Qualifiers : {', '.join(q_parts)}"

        return (
            f"{label}:\n"
            f"  Document   : {fact.document.filename}\n"
            f"  Entity     : {fact.entity}\n"
            f"  Attribute  : {fact.attribute}\n"
            f"  Value      : {fact.value}\n"
            f"  Unit       : {fact.unit or 'not specified'}\n"
            f"  Time scope : {fact.time_scope or 'not specified'}"
            f"{qualifier_str}\n"
            f"  Evidence   : {fact.raw_text}"
        )

    prompt = (
        f"{format_fact(fact_a, 'FACT A')}\n\n"
        f"{format_fact(fact_b, 'FACT B')}\n\n"
        "Compare these two facts and classify their relationship."
    )

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=COMPARISON_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=ComparisonResult,
                ),
            )

            return ComparisonResult.model_validate_json(response.text)

        except Exception as exc:
            if attempt == max_retries - 1:
                raise

            delay = 2 ** attempt
            print(
                f"Gemini comparison failed "
                f"(attempt {attempt + 1}/{max_retries}). "
                f"Retrying in {delay}s... Error: {exc}"
            )
            time.sleep(delay)

    raise RuntimeError("Unreachable")


def already_compared(db: Session, fact_a_id, fact_b_id) -> bool:
    """Check if this pair has already been compared (in either order)."""
    return db.query(Relationship).filter(
        (
            (Relationship.fact_a_id == fact_a_id) &
            (Relationship.fact_b_id == fact_b_id)
        ) | (
            (Relationship.fact_a_id == fact_b_id) &
            (Relationship.fact_b_id == fact_a_id)
        )
    ).first() is not None


def run_comparison_for_document(
    db: Session,
    document_id,
    search_limit: int = 5,
) -> int:
    """
    For every embedded fact in a document, find similar facts from other
    documents and classify the relationship via Gemini.

    Skips pairs that have already been compared.
    Returns the total number of relationships saved.
    """
    facts = (
        db.query(Fact)
        .filter(
            Fact.document_id == document_id,
            Fact.embedding.is_not(None),
        )
        .all()
    )

    total_relationships = 0

    for index, fact in enumerate(facts, start=1):
        print(
            f"\n[{index}/{len(facts)}] "
            f"Comparing: {fact.entity} | {fact.attribute} | {fact.time_scope}"
        )

        candidates = find_similar_facts(db, fact, limit=search_limit)

        if not candidates:
            print("  → no similar facts found")
            continue

        for candidate, score in candidates:
            if already_compared(db, fact.id, candidate.id):
                print(f"  → already compared with {candidate.id}, skipping")
                continue

            print(
                f"  → comparing with: {candidate.entity} | "
                f"{candidate.attribute} | {candidate.time_scope} "
                f"(score: {score:.3f})"
            )

            try:
                result = compare_facts(fact, candidate)

                if result.relationship_type == RelationshipType.UNRELATED:
                    print(f"  → unrelated, skipping")
                    continue

                relationship = Relationship(
                    fact_a_id=fact.id,
                    fact_b_id=candidate.id,
                    relationship_type=result.relationship_type.value,
                    explanation=result.explanation,
                    confidence=result.confidence,
                )

                db.add(relationship)
                db.commit()

                total_relationships += 1

                print(
                    f"  → {result.relationship_type.value} "
                    f"(confidence: {result.confidence:.2f})"
                )
                print(f"     {result.explanation[:120]}...")

            except Exception as exc:
                print(f"  → comparison FAILED: {exc}")
                continue

    return total_relationships
