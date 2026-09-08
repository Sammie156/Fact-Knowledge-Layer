from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from api.deps import get_db
from api.schemas import StatsOut
from core.models import Document, Chunk, Fact, Relationship

router = APIRouter(tags=["Stats & System"])


@router.get("/stats", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db)):
    """Summary metrics of the knowledge layer."""
    doc_count = db.query(func.count(Document.id)).scalar() or 0
    chunk_count = db.query(func.count(Chunk.id)).scalar() or 0
    fact_count = db.query(func.count(Fact.id)).scalar() or 0
    rel_count = db.query(func.count(Relationship.id)).scalar() or 0

    rel_types_query = (
        db.query(Relationship.relationship_type, func.count(Relationship.id))
        .group_by(Relationship.relationship_type)
        .all()
    )
    rel_types = {rtype: count for rtype, count in rel_types_query}

    return StatsOut(
        total_documents=doc_count,
        total_chunks=chunk_count,
        total_facts=fact_count,
        total_relationships=rel_count,
        relationships_by_type=rel_types,
    )


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """System health check verifying database and service readiness."""
    try:
        db.execute(func.now())
        db_status = "connected"
    except Exception as exc:
        db_status = f"error: {exc}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "service": "Fact Knowledge Layer API",
        "version": "1.0.0",
    }
