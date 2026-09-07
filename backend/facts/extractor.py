from google import genai
from google.genai import types

from core.config import settings
from facts.schemas import FactExtractionResult


client = genai.Client(
    api_key=settings.gemini_api_key
)


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


def extract_facts(chunk_text: str) -> FactExtractionResult:

    prompt = f"""
Extract factual claims from this document chunk.

DOCUMENT CHUNK:
----------------
{chunk_text}
----------------
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=FactExtractionResult,
        ),
    )

    return FactExtractionResult.model_validate_json(
        response.text
    )