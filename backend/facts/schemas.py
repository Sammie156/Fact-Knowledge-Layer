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
    facts: list[Fact] = Field(default_factory=list)