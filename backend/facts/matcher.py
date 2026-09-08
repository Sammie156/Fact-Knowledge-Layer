from core.models import Fact


# Canonical name → set of aliases that should resolve to it.
# All values must be lowercase.
ENTITY_ALIASES: dict[str, set[str]] = {
    "delhivery": {
        "delhivery limited",
        "delhivery ltd",
        "the company",
        "company",
        "the issuer",
        "issuer",
    },
    "india": {
        "goi",
        "government of india",
        "republic of india",
        "indian government",
        "rbi",
        "reserve bank of india",
        "ministry of finance",
    },
}

# Attributes that are semantically equivalent across documents.
# All values must be lowercase.
ATTRIBUTE_ALIASES: dict[str, set[str]] = {
    "revenue from operations": {
        "revenue",
        "net revenue",
        "total revenue",
        "revenue from services",
        "operating revenue",
    },
    "total income": {
        "total revenue",
        "gross income",
        "income",
    },
    "ebitda": {
        "adjusted ebitda",
        "operating ebitda",
        "ebitda margin",
    },
    "profit after tax": {
        "pat",
        "net profit",
        "net income",
        "profit for the year",
        "profit for the period",
    },
    "gdp growth": {
        "gdp growth rate",
        "real gdp growth",
        "economic growth",
        "gdp",
    },
}


def normalize_text(value: str | None) -> str:
    if not value:
        return ""

    return (
        value.lower()
        .strip()
        .replace("_", " ")
        .replace("-", " ")
    )


def resolve_entity(entity: str) -> str:
    """Normalize an entity string to its canonical form."""
    normalized = normalize_text(entity)
    for canonical, aliases in ENTITY_ALIASES.items():
        if normalized == canonical or normalized in aliases:
            return canonical
    return normalized


def resolve_attribute(attribute: str) -> str:
    """Normalize an attribute string to its canonical form."""
    normalized = normalize_text(attribute)
    for canonical, aliases in ATTRIBUTE_ALIASES.items():
        if normalized == canonical or normalized in aliases:
            return canonical
    return normalized


def entity_similarity(a: Fact, b: Fact) -> float:
    entity_a = resolve_entity(a.entity)
    entity_b = resolve_entity(b.entity)

    if not entity_a or not entity_b:
        return 0.5

    if entity_a == entity_b:
        return 1.0

    if entity_a in entity_b or entity_b in entity_a:
        return 0.8

    # Don't hard-zero — entity naming is inconsistent across documents.
    # Let vector similarity carry mismatched entities.
    return 0.2


def attribute_similarity(a: Fact, b: Fact) -> float:
    attribute_a = resolve_attribute(a.attribute)
    attribute_b = resolve_attribute(b.attribute)

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

    # Gemini will reason about "FY24" vs "FY ended March 31, 2024".
    # Return 0.5 rather than 0 — different periods are still worth comparing.
    return 0.5


def unit_compatibility(a: Fact, b: Fact) -> float:
    unit_a = normalize_text(a.unit)
    unit_b = normalize_text(b.unit)

    if not unit_a or not unit_b:
        return 0.5

    if unit_a == unit_b:
        return 1.0

    # Different units may represent the same quantity (INR Million vs ₹ Cr).
    # Gemini handles the reconciliation later.
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
