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

    parts = [
        f"Entity: {entity}",
        f"Attribute: {attribute}",
        f"Value: {value}",
    ]

    if unit:
        parts.append(f"Unit: {unit}")

    if time_scope:
        parts.append(f"Time scope: {time_scope}")

    if qualifiers:
        parts.append(f"Qualifiers: {qualifiers}")

    return "\n".join(parts)


def generate_embedding(text: str) -> list[float]:

    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
        config=types.EmbedContentConfig(
            output_dimensionality=768,
        ),
    )

    return response.embeddings[0].values