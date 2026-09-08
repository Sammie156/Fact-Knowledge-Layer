from facts.gemini_client import extract_facts_with_retry, extract_facts_batch
from facts.schemas import FactExtractionResult, BatchExtractionResult


def extract_facts(chunk_text: str) -> FactExtractionResult:
    """Extract facts from a single chunk. Used by tests and direct calls."""
    return extract_facts_with_retry(chunk_text)


def extract_facts_in_batch(
    chunks: list[tuple[int, str]],
) -> BatchExtractionResult:
    """Extract facts from multiple chunks in one Gemini call."""
    return extract_facts_batch(chunks)
