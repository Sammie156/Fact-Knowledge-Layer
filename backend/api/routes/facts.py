from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from api.deps import get_db
from api.schemas import FactOut, QualifierItem
from core.models import Fact, Document

router = APIRouter(prefix="/facts", tags=["Facts"])


def map_fact_to_out(fact: Fact, doc_filename: str | None = None) -> FactOut:
    qualifiers = [
        QualifierItem(key=q.get("key", ""), value=str(q.get("value", "")))
        for q in (fact.qualifiers or [])
        if isinstance(q, dict)
    ]
    return FactOut(
        id=fact.id,
        document_id=fact.document_id,
        document_filename=doc_filename or (fact.document.filename if fact.document else None),
        chunk_id=fact.chunk_id,
        page_number=fact.page_number,
        entity=fact.entity,
        attribute=fact.attribute,
        value=fact.value,
        unit=fact.unit,
        time_scope=fact.time_scope,
        qualifiers=qualifiers,
        raw_text=fact.raw_text,
        confidence=fact.confidence,
    )


@router.get("", response_model=list[FactOut])
def list_facts(
    document_id: UUID | None = Query(None, description="Filter by document ID"),
    entity: str | None = Query(None, description="Filter by entity name (case-insensitive substring)"),
    attribute: str | None = Query(None, description="Filter by attribute name (case-insensitive substring)"),
    search: str | None = Query(None, description="Search across entity, attribute, value, or raw text"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Search and list extracted facts across the knowledge layer.
    Every fact includes its page number and exact grounded source evidence.
    """
    query = db.query(Fact, Document.filename).join(Document, Fact.document_id == Document.id)

    if document_id:
        query = query.filter(Fact.document_id == document_id)

    if entity:
        query = query.filter(Fact.entity.ilike(f"%{entity}%"))

    if attribute:
        query = query.filter(Fact.attribute.ilike(f"%{attribute}%"))

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Fact.entity.ilike(search_pattern),
                Fact.attribute.ilike(search_pattern),
                Fact.value.ilike(search_pattern),
                Fact.raw_text.ilike(search_pattern),
            )
        )

    results = query.order_by(Fact.page_number.asc(), Fact.confidence.desc()).offset(offset).limit(limit).all()

    return [map_fact_to_out(fact, filename) for fact, filename in results]


@router.get("/{fact_id}", response_model=FactOut)
def get_fact(fact_id: UUID, db: Session = Depends(get_db)):
    """Retrieve full details of a specific fact."""
    fact = db.get(Fact, fact_id)
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")

    return map_fact_to_out(fact)
