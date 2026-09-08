from facts.gemini_client import extract_facts_with_retry
from facts.schemas import FactExtractionResult


def extract_facts(chunk_text: str) -> FactExtractionResult:
    return extract_facts_with_retry(chunk_text)