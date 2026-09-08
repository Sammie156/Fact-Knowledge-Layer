import re

# Matches any number: 1,234 or 1.5 or 18,793 or 8.2 or 45000
NUMBER_PATTERN = re.compile(r"\b\d[\d,]*(?:\.\d+)?")

# Matches percentages explicitly
PERCENTAGE_PATTERN = re.compile(r"\d+(?:\.\d+)?\s*%")

# Matches global currency symbols and codes
CURRENCY_PATTERN = re.compile(r"[₹$€£¥]\s*\d|INR|USD|EUR|GBP|JPY")

FACTUAL_WORDS = [
    # Financial & metrics
    "revenue",
    "profit",
    "loss",
    "income",
    "expense",
    "ebitda",
    "margin",
    "growth",
    "sales",
    "earnings",
    "dividend",
    "cash flow",
    "debt",
    "equity",
    "assets",
    "liabilities",
    "valuation",
    "expenditure",
    "budget",
    "cost",
    # Operational & scale
    "employees",
    "headcount",
    "customers",
    "users",
    "orders",
    "volume",
    "capacity",
    "network",
    "production",
    "units",
    "subscribers",
    # Macro & market
    "gdp",
    "inflation",
    "interest rate",
    "exports",
    "imports",
    "deficit",
    "surplus",
    "index",
    # Reporting periods
    "fy",
    "fiscal",
    "year ended",
    "quarter",
    "q1",
    "q2",
    "q3",
    "q4",
    "annual",
]

SEMANTIC_SIGNALS = [
    "expanded",
    "launched",
    "acquired",
    "entered",
    "opened",
    "closed",
    "appointed",
    "resigned",
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
    "established",
    "founded",
    "partnered",
    "approved",
    "certified",
]

GOVERNANCE_SIGNALS = [
    "director",
    "managing director",
    "executive",
    "ceo",
    "cfo",
    "cto",
    "board of directors",
    "resignation",
    "appointment",
    "headquarters",
    "headquartered",
    "registered office",
    "subsidiary",
    "merger",
    "acquisition",
    "auditor",
]


def looks_fact_bearing(text: str) -> bool:
    """
    Returns True if the chunk is likely to contain at least one
    extractable factual claim (numerical or semantic).

    Accepts:
      1. Numerical facts: contains a number/currency/percent AND a factual keyword
         or semantic action.
      2. Non-numerical semantic facts: contains a governance/corporate signal AND
         a semantic action (e.g. appointments, resignations, headquarters, mergers).
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

    has_factual_word = any(word in text_lower for word in FACTUAL_WORDS)
    has_semantic_signal = any(word in text_lower for word in SEMANTIC_SIGNALS)
    has_governance = any(word in text_lower for word in GOVERNANCE_SIGNALS)

    # 1. Quantitative facts: numbers accompanied by metrics or actions
    if has_number and (has_factual_word or has_semantic_signal or has_governance):
        return True

    # 2. Pure semantic facts: governance/corporate state changes (even without numbers)
    if has_governance and has_semantic_signal:
        return True

    return False
