import re

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
]


def looks_fact_bearing(text: str) -> bool:
    text = text.strip()

    if not text or len(text) < 20:
        return False

    text_lower = text.lower()

    # Percentages
    if re.search(r"\d+(?:\.\d+)?\s*%", text):
        return True

    # Currency
    if any(symbol in text for symbol in ["₹", "$", "€", "£"]):
        return True

    factual_words = [
        "revenue",
        "profit",
        "loss",
        "income",
        "expense",
        "growth",
        "employees",
        "customers",
        "users",
        "orders",
        "shipments",
        "FY",
        "fiscal",
        "year ended",
    ]

    if any(word.lower() in text_lower for word in factual_words):
        return True

    semantic_signals = [
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
    ]

    if any(word in text_lower for word in semantic_signals):
        return True

    return False