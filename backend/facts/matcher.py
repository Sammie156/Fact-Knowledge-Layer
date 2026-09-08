import re
from core.models import Fact


LEGAL_SUFFIXES = {
    "ltd",
    "limited",
    "inc",
    "incorporated",
    "corp",
    "corporation",
    "co",
    "company",
    "plc",
    "llc",
    "pvt",
    "private",
    "holdings",
    "group",
}

GENERIC_ENTITIES = {
    "the company",
    "company",
    "the issuer",
    "issuer",
    "the organization",
    "organization",
    "the government",
    "government",
}

STOP_WORDS = {
    "the", "of", "and", "in", "to", "for", "from", "a", "an", "on", "at", "by"
}

YEAR_PATTERN = re.compile(r"\b(19\d\d|20\d\d)\b")


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"[^\w\s]", " ", value.lower())
    return " ".join(cleaned.split())


def clean_entity(entity: str | None) -> tuple[str, set[str]]:
    """
    Returns (cleaned_string, token_set) with legal suffixes stripped.
    """
    normalized = normalize_text(entity)
    tokens = [t for t in normalized.split() if t not in LEGAL_SUFFIXES]
    return " ".join(tokens), set(tokens)


def entity_similarity(a: Fact, b: Fact) -> float:
    """
    Domain-agnostic entity similarity based on token overlap,
    substring matching, and legal suffix normalization.
    """
    norm_a = normalize_text(a.entity)
    norm_b = normalize_text(b.entity)

    if not norm_a or not norm_b:
        return 0.5

    # If either refers to generic self-reference, let vector similarity guide
    if norm_a in GENERIC_ENTITIES or norm_b in GENERIC_ENTITIES:
        return 0.6

    clean_a, tokens_a = clean_entity(a.entity)
    clean_b, tokens_b = clean_entity(b.entity)

    if clean_a == clean_b and clean_a:
        return 1.0

    if clean_a and clean_b and (clean_a in clean_b or clean_b in clean_a):
        return 0.9

    if tokens_a and tokens_b:
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        jaccard = len(intersection) / len(union)
        if jaccard > 0:
            return 0.4 + (0.5 * jaccard)

    # Disjoint distinct named entities
    return 0.15


def attribute_similarity(a: Fact, b: Fact) -> float:
    """
    Domain-agnostic attribute similarity using token overlap.
    """
    norm_a = normalize_text(a.attribute)
    norm_b = normalize_text(b.attribute)

    if not norm_a or not norm_b:
        return 0.5

    if norm_a == norm_b:
        return 1.0

    if norm_a in norm_b or norm_b in norm_a:
        return 0.85

    tokens_a = {t for t in norm_a.split() if t not in STOP_WORDS}
    tokens_b = {t for t in norm_b.split() if t not in STOP_WORDS}

    if tokens_a and tokens_b:
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        jaccard = len(intersection) / len(union)
        if jaccard > 0:
            return 0.3 + (0.6 * jaccard)

    # If no token overlap, return a modest baseline to let vector similarity bridge synonyms
    return 0.25


def time_compatibility(a: Fact, b: Fact) -> float:
    """
    Compare time scopes without assuming specific formats.
    """
    time_a = normalize_text(a.time_scope)
    time_b = normalize_text(b.time_scope)

    if not time_a or not time_b:
        return 0.6

    if time_a == time_b:
        return 1.0

    years_a = set(YEAR_PATTERN.findall(time_a))
    years_b = set(YEAR_PATTERN.findall(time_b))

    if years_a and years_b:
        if years_a & years_b:
            return 0.9
        # Different years may be compared for context_explained reconciliations
        return 0.5

    if time_a in time_b or time_b in time_a:
        return 0.85

    return 0.5


def unit_compatibility(a: Fact, b: Fact) -> float:
    """
    Compare units without hardcoding conversions.
    """
    unit_a = normalize_text(a.unit)
    unit_b = normalize_text(b.unit)

    if not unit_a or not unit_b:
        return 0.6

    if unit_a == unit_b:
        return 1.0

    # Different units might be reconcilable by LLM (e.g. INR vs USD, millions vs billions)
    return 0.5


def structural_score(a: Fact, b: Fact) -> float:
    """
    Combines domain-agnostic entity, attribute, time, and unit compatibility.
    """
    entity_score = entity_similarity(a, b)
    attribute_score = attribute_similarity(a, b)
    time_score = time_compatibility(a, b)
    unit_score = unit_compatibility(a, b)

    return (
        entity_score * 0.40
        + attribute_score * 0.40
        + time_score * 0.10
        + unit_score * 0.10
    )


def candidate_score(
    query_fact: Fact,
    candidate_fact: Fact,
    vector_similarity: float,
) -> float:
    """
    Blends embedding semantic similarity (60%) with domain-agnostic
    structural alignment (40%).
    """
    structure = structural_score(query_fact, candidate_fact)
    return (vector_similarity * 0.60) + (structure * 0.40)
