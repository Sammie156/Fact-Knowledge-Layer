import time

from google import genai
from google.genai import types

from core.config import settings
from facts.schemas import FactExtractionResult, BatchExtractionResult


client = genai.Client(api_key=settings.gemini_api_key)


SYSTEM_PROMPT = """
You are a factual information extraction system.

Extract meaningful factual claims from the provided document chunk.

A fact should represent a claim that could be compared with
facts extracted from another document.

Extract:
- numerical facts
- dates and periods
- quantities
- percentages
- business metrics
- named entities and their attributes
- meaningful semantic facts

Entity normalization rules:
- Resolve self-referential terms ("the Company", "the Issuer", "the Corporation", "the Government", "we", "our") to the canonical entity name identified from the document context.
- Use the standard canonical entity name without trailing legal corporate suffixes (e.g. use "Acme" instead of "Acme Limited" or "Acme Inc.") unless the distinction between distinct legal subsidiaries is legally significant.
- Specific operational divisions or segments are attributes/qualifiers rather than independent entities unless the fact is strictly specific to that division with no parent context.
- For macroeconomic or jurisdictional facts, use the standardized name of the nation, state, or institution (e.g., "India" rather than "GoI", "Federal Reserve" rather than "the Fed").

Qualifiers and context:
- Always capture contextual qualifiers where present or inferable (e.g., basis: "standalone" vs "consolidated", nature: "audited" vs "unaudited" vs "provisional", scope: "domestic" vs "international").
- If tabular data or reports present multiple perspectives (such as standalone vs consolidated, or revised vs provisional), extract each distinct figure as a separate fact with its respective qualifiers — do not merge them.

Do not extract:
- headings by themselves
- generic statements with no meaningful factual content
- legal boilerplate unless it contains a meaningful fact
- instructions or navigation text

For every extracted fact:
- preserve the meaning of the source text
- do not invent information
- preserve units and time periods
- preserve qualifiers such as standalone/consolidated
- raw_text must contain the source wording supporting the fact
- confidence should reflect how clearly the chunk supports the fact
"""


def extract_facts_batch(
    chunks: list[tuple[int, str]],  # (chunk_index, content)
    max_retries: int = 3,
) -> BatchExtractionResult:
    """
    Extract facts from multiple chunks in a single Gemini call.

    chunks is a list of (chunk_index, content) tuples. chunk_index is
    the position within the batch (0-based) and is echoed back in the
    response so each fact can be attributed to the right chunk.

    Using batches reduces API calls by ~5x and keeps us within free
    tier rate limits without aggressive sleeping.
    """
    formatted = "\n\n".join(
        f"CHUNK {idx}:\n{'-' * 40}\n{content}\n{'-' * 40}"
        for idx, content in chunks
    )

    prompt = f"""
Extract factual claims from each numbered chunk below.

For each chunk return its chunk_index and all facts found in it.
If a chunk contains no extractable facts, return an empty facts list for it.
Every chunk must appear in your response even if it has no facts.

{formatted}
"""

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=BatchExtractionResult,
                ),
            )

            return BatchExtractionResult.model_validate_json(response.text)

        except Exception as exc:
            if attempt == max_retries - 1:
                raise

            delay = 2 ** attempt
            print(
                f"Gemini batch request failed "
                f"(attempt {attempt + 1}/{max_retries}). "
                f"Retrying in {delay}s... Error: {exc}"
            )
            time.sleep(delay)

    raise RuntimeError("Unreachable")


# ------------------------------------------------------------------
# Single-chunk extraction kept for backwards compatibility
# (used by test_repo.py and any direct calls)
# ------------------------------------------------------------------

def extract_facts_with_retry(
    chunk_text: str,
    max_retries: int = 3,
) -> FactExtractionResult:
    """Extract facts from a single chunk."""

    prompt = f"""
Extract factual claims from this document chunk.

DOCUMENT CHUNK:
----------------
{chunk_text}
----------------
"""

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=FactExtractionResult,
                ),
            )

            return FactExtractionResult.model_validate_json(response.text)

        except Exception as exc:
            if attempt == max_retries - 1:
                raise

            delay = 2 ** attempt
            print(
                f"Gemini request failed "
                f"(attempt {attempt + 1}/{max_retries}). "
                f"Retrying in {delay}s..."
            )
            time.sleep(delay)

    raise RuntimeError("Unreachable")
