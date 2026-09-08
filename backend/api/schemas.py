from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class QualifierItem(BaseModel):
    key: str
    value: str


class DocumentBase(BaseModel):
    filename: str
    domain: str | None = None


class DocumentOut(DocumentBase):
    id: UUID
    uploaded_at: datetime
    page_count: int | None = None
    status: str
    fact_count: int = 0
    relationship_count: int = 0

    class Config:
        from_attributes = True


class DocumentDetailOut(DocumentOut):
    chunk_count: int = 0


class FactOut(BaseModel):
    id: UUID
    document_id: UUID
    document_filename: str | None = None
    chunk_id: UUID
    page_number: int
    entity: str
    attribute: str
    value: str
    unit: str | None = None
    time_scope: str | None = None
    qualifiers: list[QualifierItem] = Field(default_factory=list)
    raw_text: str = Field(description="Exact source text evidence excerpt from the document")
    confidence: float

    class Config:
        from_attributes = True


class RelationshipFactBrief(BaseModel):
    id: UUID
    document_id: UUID
    document_filename: str | None = None
    page_number: int
    entity: str
    attribute: str
    value: str
    unit: str | None = None
    time_scope: str | None = None
    raw_text: str


class RelationshipOut(BaseModel):
    id: UUID
    relationship_type: str = Field(
        description="corroborates | contradicts | context_explained"
    )
    explanation: str | None = None
    confidence: float | None = None
    created_at: datetime
    fact_a: RelationshipFactBrief
    fact_b: RelationshipFactBrief

    class Config:
        from_attributes = True


class StatsOut(BaseModel):
    total_documents: int
    total_chunks: int
    total_facts: int
    total_relationships: int
    relationships_by_type: dict[str, int]


class ShowcaseCaseItem(BaseModel):
    case_number: int
    title: str
    requirement: str
    description: str
    relationship: RelationshipOut | None = None
    details: dict | None = None


class ShowcaseResponse(BaseModel):
    overview: str
    cases: list[ShowcaseCaseItem]


class UploadResponse(BaseModel):
    message: str
    document_id: UUID
    filename: str
    status: str
    page_count: int | None = None
    facts_extracted: int | None = None
    relationships_found: int | None = None
