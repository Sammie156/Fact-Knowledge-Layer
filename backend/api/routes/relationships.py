from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session, aliased
from sqlalchemy import or_

from api.deps import get_db
from api.schemas import RelationshipOut, RelationshipFactBrief
from core.models import Relationship, Fact, Document
from facts.reasoner import run_comparison_for_document

router = APIRouter(prefix="/relationships", tags=["Relationships"])


def map_relationship(rel: Relationship, fact_a: Fact, doc_a: Document, fact_b: Fact, doc_b: Document) -> RelationshipOut:
    return RelationshipOut(
        id=rel.id,
        relationship_type=rel.relationship_type,
        explanation=rel.explanation,
        confidence=rel.confidence,
        created_at=rel.created_at,
        fact_a=RelationshipFactBrief(
            id=fact_a.id,
            document_id=fact_a.document_id,
            document_filename=doc_a.filename,
            page_number=fact_a.page_number,
            entity=fact_a.entity,
            attribute=fact_a.attribute,
            value=fact_a.value,
            unit=fact_a.unit,
            time_scope=fact_a.time_scope,
            raw_text=fact_a.raw_text,
        ),
        fact_b=RelationshipFactBrief(
            id=fact_b.id,
            document_id=fact_b.document_id,
            document_filename=doc_b.filename,
            page_number=fact_b.page_number,
            entity=fact_b.entity,
            attribute=fact_b.attribute,
            value=fact_b.value,
            unit=fact_b.unit,
            time_scope=fact_b.time_scope,
            raw_text=fact_b.raw_text,
        ),
    )


@router.get("", response_model=list[RelationshipOut])
def list_relationships(
    relationship_type: str | None = Query(
        None,
        description="Filter by type: corroborates | contradicts | context_explained"
    ),
    document_id: UUID | None = Query(
        None,
        description="Filter relationships involving a specific document"
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    List cross-document relationships discovered by the reasoning layer.
    Includes full evidence snippets and system explanations.
    """
    FactA = aliased(Fact, name="fact_a")
    FactB = aliased(Fact, name="fact_b")
    DocA = aliased(Document, name="doc_a")
    DocB = aliased(Document, name="doc_b")

    query = (
        db.query(Relationship, FactA, DocA, FactB, DocB)
        .join(FactA, Relationship.fact_a_id == FactA.id)
        .join(DocA, FactA.document_id == DocA.id)
        .join(FactB, Relationship.fact_b_id == FactB.id)
        .join(DocB, FactB.document_id == DocB.id)
    )

    if relationship_type:
        query = query.filter(Relationship.relationship_type == relationship_type.lower())

    if document_id:
        query = query.filter(
            or_(
                FactA.document_id == document_id,
                FactB.document_id == document_id,
            )
        )

    results = query.order_by(Relationship.created_at.desc()).offset(offset).limit(limit).all()

    return [
        map_relationship(rel, fact_a, doc_a, fact_b, doc_b)
        for rel, fact_a, doc_a, fact_b, doc_b in results
    ]


@router.get("/{relationship_id}", response_model=RelationshipOut)
def get_relationship(relationship_id: UUID, db: Session = Depends(get_db)):
    """Get a single cross-document relationship with complete comparative details."""
    FactA = aliased(Fact, name="fact_a")
    FactB = aliased(Fact, name="fact_b")
    DocA = aliased(Document, name="doc_a")
    DocB = aliased(Document, name="doc_b")

    result = (
        db.query(Relationship, FactA, DocA, FactB, DocB)
        .join(FactA, Relationship.fact_a_id == FactA.id)
        .join(DocA, FactA.document_id == DocA.id)
        .join(FactB, Relationship.fact_b_id == FactB.id)
        .join(DocB, FactB.document_id == DocB.id)
        .filter(Relationship.id == relationship_id)
        .first()
    )

    if not result:
        raise HTTPException(status_code=404, detail="Relationship not found")

    rel, fact_a, doc_a, fact_b, doc_b = result
    return map_relationship(rel, fact_a, doc_a, fact_b, doc_b)


@router.post("/compare", status_code=202)
def trigger_comparison(
    document_id: UUID | None = Query(None, description="Optional document ID to run comparison for"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
):
    """Trigger cross-document comparison across embedded facts."""
    docs_to_compare = []
    if document_id:
        doc = db.get(Document, document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        docs_to_compare.append(doc.id)
    else:
        all_docs = db.query(Document).filter(Document.status == "done").all()
        docs_to_compare = [d.id for d in all_docs]

    def _run_all():
        from core.database import SessionLocal
        local_db = SessionLocal()
        try:
            for doc_id in docs_to_compare:
                run_comparison_for_document(db=local_db, document_id=doc_id)
        finally:
            local_db.close()

    background_tasks.add_task(_run_all)
    return {
        "message": f"Comparison triggered for {len(docs_to_compare)} documents.",
        "document_ids": [str(d) for d in docs_to_compare],
    }
