from google import genai
from google.genai import types

from core.config import settings


client = genai.Client(api_key=settings.gemini_api_key)


text = """
Entity: Revenue
Attribute: growth rate
Value: 20
Unit: %
Time scope: FY2024
"""


response = client.models.embed_content(
    model="gemini-embedding-001",
    contents=text,
    config=types.EmbedContentConfig(
        output_dimensionality=768,
    ),
)


embedding = response.embeddings[0].values

print("Embedding dimensions:", len(embedding))
print("First 10 values:", embedding[:10])