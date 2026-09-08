import re

# Matches any number: 1,234 or 1.5 or 18,793 or 8.2 or 45000
NUMBER_PATTERN = re.compile(r"\b\d[\d,]*(?:\.\d+)?")

# Matches percentages explicitly
PERCENTAGE_PATTERN = re.compile(r"\d+(?:\.\d+)?\s*%")

# Matches Indian/global currency
CURRENCY_PATTERN = re.compile(r"[₹$€£]\s*\d|INR|USD|EUR")

FACTUAL_WORDS = [
    "revenue",
    "profit",
    "loss",
    "income",
    "expense",
    "ebitda",
    "margin",
    "growth",
    "employees",
    "headcount",
    "customers",
    "users",
    "orders",
    "shipments",
    "parcels",
    "volume",
    "capacity",
    "network",
    "pin code",
    "pincode",
    "pin-code",
    "fy",
    "fiscal",
    "year ended",
    "quarter",
    "q1",
    "q2",
    "q3",
    "q4",
    "gdp",
    "inflation",
    "cpi",
    "wpi",
    "interest rate",
    "repo rate",
    "forex",
    "trade deficit",
    "exports",
    "imports",
]

SEMANTIC_SIGNALS = [
    "expanded",
    "launched",
    "acquired",
    "entered",
    "opened",
    "closed",
    "appointed",
    "introduced",
    "increased",
    "decreased",
    "grew",
    "declined",
    "raised",
    "reduced",
    "achieved",
    "crossed",
    "reached",
]


def looks_fact_bearing(text: str) -> bool:
    """
    Returns True if the chunk is likely to contain at least one
    extractable fact worth sending to Gemini.

    Requires BOTH:
      - a concrete number or currency symbol, AND
      - a factual keyword or semantic signal

    This cuts ~50% of chunks that contain signal words like "revenue"
    or "growth" in narrative text without any actual figures.
    """
    text = text.strip()

    if not text or len(text) < 30:
        return False

    text_lower = text.lower()

    has_number = (
        bool(NUMBER_PATTERN.search(text))
        or bool(PERCENTAGE_PATTERN.search(text))
        or bool(CURRENCY_PATTERN.search(text))
    )

    # No number means no extractable fact — skip immediately
    if not has_number:
        return False

    has_factual_word = any(word in text_lower for word in FACTUAL_WORDS)
    has_semantic_signal = any(word in text_lower for word in SEMANTIC_SIGNALS)

    return has_factual_word or has_semantic_signal
