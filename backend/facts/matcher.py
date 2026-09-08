from core.models import Fact


def normalize_text(value: str | None) -> str:
    if not value:
        return ""

    return (
        value.lower()
        .strip()
        .replace("_", " ")
        .replace("-", " ")
    )


def entity_similarity(a: Fact, b: Fact) -> float:
    entity_a = normalize_text(a.entity)
    entity_b = normalize_text(b.entity)

    if not entity_a or not entity_b:
        return 0.5

    if entity_a == entity_b:
        return 1.0

    if entity_a in entity_b or entity_b in entity_a:
        return 0.8

    return 0.0


def attribute_similarity(a: Fact, b: Fact) -> float:
    attribute_a = normalize_text(a.attribute)
    attribute_b = normalize_text(b.attribute)

    if not attribute_a or not attribute_b:
        return 0.5

    if attribute_a == attribute_b:
        return 1.0

    if attribute_a in attribute_b or attribute_b in attribute_a:
        return 0.8

    return 0.0


def time_compatibility(a: Fact, b: Fact) -> float:
    time_a = normalize_text(a.time_scope)
    time_b = normalize_text(b.time_scope)

    if not time_a or not time_b:
        return 0.5

    if time_a == time_b:
        return 1.0

    # Don't attempt to determine semantic equivalence here.
    # Gemini will reason about things like:
    # "FY24" vs "FY ended March 31, 2024".
    return 0.5


def unit_compatibility(a: Fact, b: Fact) -> float:
    unit_a = normalize_text(a.unit)
    unit_b = normalize_text(b.unit)

    if not unit_a or not unit_b:
        return 0.5

    if unit_a == unit_b:
        return 1.0

    # Different units may still represent the same quantity.
    # e.g. INR Million vs ₹ Cr.
    return 0.5


def structural_score(a: Fact, b: Fact) -> float:
    entity_score = entity_similarity(a, b)
    attribute_score = attribute_similarity(a, b)
    time_score = time_compatibility(a, b)
    unit_score = unit_compatibility(a, b)

    return (
        entity_score * 0.35
        + attribute_score * 0.40
        + time_score * 0.15
        + unit_score * 0.10
    )


def candidate_score(
    query_fact: Fact,
    candidate_fact: Fact,
    vector_similarity: float,
) -> float:
    structure = structural_score(query_fact, candidate_fact)

    return (
        vector_similarity * 0.60
        + structure * 0.40
    )