from google import genai
from google.genai import types

from core.config import settings


def _get_client():
    if not settings.gemini_api_key:
        raise ValueError(
            "GEMINI_API_KEY is not configured. Please add it to your .env file or configure it in the UI Settings (⚙️)."
        )
    return genai.Client(api_key=settings.gemini_api_key)


def build_fact_text(
    entity: str,
    attribute: str,
    value: str,
    unit: str | None,
    time_scope: str | None,
    qualifiers: list | None,
) -> str:
    """
    Build a natural language sentence for embedding.

    Natural language embeds much better than structured key-value pairs
    because embedding models are trained on prose. Repeating the attribute
    increases its weight in the resulting vector, which improves recall
    when searching for facts about the same metric.
    """
    unit_str = f" {unit}" if unit else ""
    time_str = f" in {time_scope}" if time_scope else ""
    qualifier_str = ""

    if qualifiers:
        q_parts = [f"{q['key']}: {q['value']}" for q in qualifiers]
        qualifier_str = f" ({', '.join(q_parts)})"

    sentence = (
        f"{entity}: {attribute} is {value}{unit_str}{time_str}{qualifier_str}. "
        f"Fact regarding {entity} {attribute}."
    )

    return sentence


def generate_embedding(text: str) -> list[float]:
    client = _get_client()
    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
        config=types.EmbedContentConfig(
            output_dimensionality=768,
        ),
    )

    return response.embeddings[0].values


def generate_embeddings_batch(
    texts: list[str],
    max_retries: int = 3,
) -> list[list[float]]:
    """
    Generate embeddings for multiple texts in a single batch API call.
    Drastically reduces API calls and avoids per-request rate limits.
    """
    if not texts:
        return []

    client = _get_client()
    import time
    for attempt in range(max_retries):
        try:
            response = client.models.embed_content(
                model="gemini-embedding-001",
                contents=texts,
                config=types.EmbedContentConfig(
                    output_dimensionality=768,
                ),
            )
            return [e.values for e in response.embeddings]
        except Exception as exc:
            if attempt == max_retries - 1:
                raise
            delay = 2 ** attempt
            print(f"[Embeddings] Batch embedding attempt {attempt + 1} failed ({exc}). Retrying in {delay}s...")
            time.sleep(delay)

    raise RuntimeError("Unreachable")
