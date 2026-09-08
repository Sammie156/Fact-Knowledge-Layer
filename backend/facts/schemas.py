from pydantic import BaseModel, Field


class Qualifier(BaseModel):
    key: str
    value: str


class Fact(BaseModel):
    entity: str
    attribute: str
    value: str
    unit: str | None = None
    time_scope: str | None = None
    qualifiers: list[Qualifier] = Field(default_factory=list)
    raw_text: str
    confidence: float = Field(ge=0.0, le=1.0)


class FactExtractionResult(BaseModel):
    """Single-chunk extraction result. Used by save_facts()."""
    facts: list[Fact] = Field(default_factory=list)


# ------------------------------------------------------------------
# Batch extraction — one Gemini call for multiple chunks
# ------------------------------------------------------------------

class ChunkExtractionResult(BaseModel):
    """Facts extracted from one chunk within a batch."""
    chunk_index: int = Field(
        description="The index of the chunk within the batch (0-based)."
    )
    facts: list[Fact] = Field(default_factory=list)


class BatchExtractionResult(BaseModel):
    """Result of a batched extraction call covering multiple chunks."""
    chunks: list[ChunkExtractionResult] = Field(default_factory=list)
