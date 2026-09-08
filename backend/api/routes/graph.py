from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from api.deps import get_db
from core.models import Document, Fact, Relationship

router = APIRouter(prefix="/graph", tags=["Graph Visualization"])


class GraphNode(BaseModel):
    id: str
    label: str
    type: str = Field(description="'document' | 'fact'")
    radius: int
    document_id: str | None = None
    document_filename: str | None = None
    page_number: int | None = None
    entity: str | None = None
    attribute: str | None = None
    value: str | None = None
    unit: str | None = None
    time_scope: str | None = None
    raw_text: str | None = None
    confidence: float | None = None
    facts_count: int | None = None


class GraphLink(BaseModel):
    source: str
    target: str
    type: str = Field(description="'contains' | 'corroborates' | 'contradicts' | 'context_explained'")
    explanation: str | None = None
    confidence: float | None = None


class GraphDataResponse(BaseModel):
    nodes: list[GraphNode]
    links: list[GraphLink]


@router.get("", response_model=GraphDataResponse)
def get_graph_data(
    include_isolated: bool = Query(True, description="Include facts with no cross-document links"),
    max_facts: int = Query(200, ge=10, le=500),
    db: Session = Depends(get_db),
):
    """
    Returns graph representation of documents, facts, and relationships
    tailored for force-directed interactive visualization (Obsidian-style).
    """
    documents = db.query(Document).all()
    doc_lookup = {str(d.id): d.filename for d in documents}

    # Fetch relationships
    relationships = db.query(Relationship).all()
    connected_fact_ids = set()
    for rel in relationships:
        connected_fact_ids.add(str(rel.fact_a_id))
        connected_fact_ids.add(str(rel.fact_b_id))

    # Fetch facts
    fact_query = db.query(Fact)
    if not include_isolated and connected_fact_ids:
        fact_query = fact_query.filter(Fact.id.in_([UUID(fid) for fid in connected_fact_ids]))

    facts = fact_query.limit(max_facts).all()
    included_fact_ids = {str(f.id) for f in facts}

    nodes: list[GraphNode] = []
    links: list[GraphLink] = []

    # 1. Document Nodes (Planetary Hubs)
    for doc in documents:
        doc_id = str(doc.id)
        doc_facts_count = sum(1 for f in facts if str(f.document_id) == doc_id)
        nodes.append(
            GraphNode(
                id=doc_id,
                label=doc.filename,
                type="document",
                radius=18,
                facts_count=doc_facts_count,
            )
        )

    # 2. Fact Nodes (Particles)
    for fact in facts:
        fact_id = str(fact.id)
        doc_id = str(fact.document_id)

        # Label: Entity: Attribute (truncated)
        short_attr = fact.attribute if len(fact.attribute) <= 22 else f"{fact.attribute[:20]}..."
        label = f"{fact.entity}: {short_attr}"

        nodes.append(
            GraphNode(
                id=fact_id,
                label=label,
                type="fact",
                radius=8,
                document_id=doc_id,
                document_filename=doc_lookup.get(doc_id),
                page_number=fact.page_number,
                entity=fact.entity,
                attribute=fact.attribute,
                value=fact.value,
                unit=fact.unit,
                time_scope=fact.time_scope,
                raw_text=fact.raw_text,
                confidence=fact.confidence,
            )
        )

        # Structural containment link: Document -> Fact
        links.append(
            GraphLink(
                source=doc_id,
                target=fact_id,
                type="contains",
            )
        )

    # 3. Cross-Document Semantic Relationship Links (Fact A <-> Fact B)
    for rel in relationships:
        src = str(rel.fact_a_id)
        tgt = str(rel.fact_b_id)

        # Only add link if both nodes are present in the visualization subset
        if src in included_fact_ids and tgt in included_fact_ids:
            links.append(
                GraphLink(
                    source=src,
                    target=tgt,
                    type=rel.relationship_type,
                    explanation=rel.explanation,
                    confidence=rel.confidence,
                )
            )

    return GraphDataResponse(nodes=nodes, links=links)
