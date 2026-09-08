from google import genai
from google.genai import types

from core.config import settings


client = genai.Client(
    api_key=settings.gemini_api_key
)

def build_fact_text(
    entity: str,
    attribute: str,
    value: str,
    unit: str | None,
    time_scope: str | None,
    qualifiers: list | None,
) -> str:
    # Build a natural language sentence instead of structured key-value
    # This gives the embedding model much more to work with
    
    unit_str = f" {unit}" if unit else ""
    time_str = f" in {time_scope}" if time_scope else ""
    qualifier_str = ""
    
    if qualifiers:
        q_parts = [f"{q['key']}: {q['value']}" for q in qualifiers]
        qualifier_str = f" ({', '.join(q_parts)})"
    
    sentence = (
        f"{entity} {attribute} was {value}{unit_str}{time_str}{qualifier_str}."
    )
    
    return sentence


def generate_embedding(text: str) -> list[float]:

    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
        config=types.EmbedContentConfig(
            output_dimensionality=768,
        ),
    )

    return response.embeddings[0].values