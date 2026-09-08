import os
import shutil
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, delete, func

from api.deps import get_db
from api.schemas import DocumentOut, DocumentDetailOut, UploadResponse
from core.database import SessionLocal
from core.models import Document, Chunk, Fact, Relationship
from ingestion.pdf_extractor import extract_pdf
from ingestion.chunker import chunk_page
from facts.pipeline import process_document
from facts.reasoner import run_comparison_for_document

router = APIRouter(prefix="/documents", tags=["Documents"])

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def run_pipeline_sync(document_id: UUID, pdf_path: str):
    """Background worker or sync runner for the full document pipeline."""
    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if not document:
            return

        document.status = "extracting_facts"
        db.commit()

        # Step 1: Fact extraction, deduplication, and embedding
        facts_count = process_document(db=db, document_id=document.id)

        # Step 2: Cross-document relationship comparison
        document.status = "comparing_facts"
        db.commit()

        relationships_count = run_comparison_for_document(db=db, document_id=document.id)

        document.status = "done"
        db.commit()
        print(f"[Pipeline] Finished {document.filename}: {facts_count} facts, {relationships_count} relationships.")
    except Exception as exc:
        err_str = str(exc)
        print(f"[Pipeline] Error processing {document_id}: {err_str}")
        document = db.get(Document, document_id)
        if document:
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                document.status = "quota_exceeded"
                document.error_message = (
                    "LLM rate limit / daily quota reached (429 RESOURCE_EXHAUSTED). "
                    "Switch to Groq or provide a new API key in Settings (⚙️)."
                )
            elif "Groq Error" in err_str or "model_not_found" in err_str:
                document.status = "failed"
                document.error_message = err_str
            else:
                document.status = "failed"
                document.error_message = err_str[:300]
            db.commit()
    finally:
        db.close()


@router.post("/upload", response_model=UploadResponse, status_code=202)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF document to ingest and analyze"),
    background: bool = Query(
        True,
        description="If True (recommended), processes asynchronously in the background. If False, waits until complete."
    ),
    replace: bool = Query(
        False,
        description="If True, re-processes and replaces an existing document with the same filename."
    ),
    db: Session = Depends(get_db),
):
    """
    Upload a PDF document. Extracts pages, creates chunks, extracts grounded facts via Gemini,
    generates embeddings, and runs cross-document relationship reasoning against all existing documents.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_path = UPLOAD_DIR / file.filename

    # Check for existing document
    existing = db.query(Document).filter(Document.filename == file.filename).first()
    if existing:
        if replace:
            # Delete relationships referencing facts of this document
            fact_ids = [f.id for f in existing.facts]
            if fact_ids:
                db.execute(
                    delete(Relationship).where(
                        (Relationship.fact_a_id.in_(fact_ids)) |
                        (Relationship.fact_b_id.in_(fact_ids))
                    )
                )
            db.delete(existing)
            db.commit()
        else:
            fact_count = db.query(Fact).filter(Fact.document_id == existing.id).count()
            return UploadResponse(
                message="Document already exists. Pass replace=true to re-process.",
                document_id=existing.id,
                filename=existing.filename,
                status=existing.status,
                page_count=existing.page_count,
                facts_extracted=fact_count,
            )

    # Save file to disk
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Extract logical pages and chunks
    try:
        pages = extract_pdf(str(file_path))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to read PDF: {exc}")

    document = Document(
        filename=file.filename,
        page_count=len(pages),
        status="processing",
    )
    db.add(document)
    db.flush()

    for page in pages:
        chunks = chunk_page(page)
        for chunk_data in chunks:
            chunk = Chunk(
                document_id=document.id,
                page_number=page.logical_page_index + 1,
                chunk_index=chunk_data.chunk_index,
                content=chunk_data.content,
                chunk_type=chunk_data.chunk_type,
                has_facts=False,
            )
            db.add(chunk)

    db.commit()

    if background:
        background_tasks.add_task(run_pipeline_sync, document.id, str(file_path))
        return UploadResponse(
            message="PDF uploaded successfully. Extraction and comparison running in background.",
            document_id=document.id,
            filename=document.filename,
            status="processing",
            page_count=len(pages),
        )
    else:
        # Run synchronously
        run_pipeline_sync(document.id, str(file_path))
        db.refresh(document)
        fact_count = db.query(Fact).filter(Fact.document_id == document.id).count()
        rel_count = db.query(Relationship).join(
            Fact, Relationship.fact_a_id == Fact.id
        ).filter(Fact.document_id == document.id).count()

        return UploadResponse(
            message="PDF processed and cross-document reasoning completed.",
            document_id=document.id,
            filename=document.filename,
            status=document.status,
            page_count=document.page_count,
            facts_extracted=fact_count,
            relationships_found=rel_count,
        )


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)):
    """List all ingested documents with status, page counts, and fact counts."""
    documents = db.query(Document).order_by(Document.uploaded_at.desc()).all()
    results = []
    for doc in documents:
        fact_count = db.query(func.count(Fact.id)).filter(Fact.document_id == doc.id).scalar() or 0
        
        # Count relationships involving facts from this document
        rel_count = db.query(func.count(Relationship.id)).join(
            Fact, (Relationship.fact_a_id == Fact.id) | (Relationship.fact_b_id == Fact.id)
        ).filter(Fact.document_id == doc.id).scalar() or 0

        results.append(
            DocumentOut(
                id=doc.id,
                filename=doc.filename,
                domain=doc.domain,
                uploaded_at=doc.uploaded_at,
                page_count=doc.page_count,
                status=doc.status,
                error_message=doc.error_message,
                fact_count=fact_count,
                relationship_count=rel_count,
            )
        )
    return results


@router.post("/reset", status_code=200)
def reset_knowledge_layer(db: Session = Depends(get_db)):
    """
    Completely reset the knowledge layer.
    Deletes all relationships, facts, chunks, and documents, and cleans up uploaded files.
    """
    db.execute(delete(Relationship))
    db.execute(delete(Fact))
    db.execute(delete(Chunk))
    db.execute(delete(Document))
    db.commit()

    if UPLOAD_DIR.exists():
        for item in UPLOAD_DIR.iterdir():
            if item.is_file():
                try:
                    item.unlink()
                except Exception:
                    pass

    return {
        "message": "Knowledge layer reset successfully. All documents, chunks, facts, and relationships have been deleted."
    }


@router.get("/{document_id}", response_model=DocumentDetailOut)
def get_document(document_id: UUID, db: Session = Depends(get_db)):
    """Get status and details of a single document."""
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    fact_count = db.query(func.count(Fact.id)).filter(Fact.document_id == doc.id).scalar() or 0
    chunk_count = db.query(func.count(Chunk.id)).filter(Chunk.document_id == doc.id).scalar() or 0
    rel_count = db.query(func.count(Relationship.id)).join(
        Fact, (Relationship.fact_a_id == Fact.id) | (Relationship.fact_b_id == Fact.id)
    ).filter(Fact.document_id == doc.id).scalar() or 0

    return DocumentDetailOut(
        id=doc.id,
        filename=doc.filename,
        domain=doc.domain,
        uploaded_at=doc.uploaded_at,
        page_count=doc.page_count,
        status=doc.status,
        error_message=doc.error_message,
        fact_count=fact_count,
        relationship_count=rel_count,
        chunk_count=chunk_count,
    )


@router.delete("/{document_id}", status_code=200)
def delete_document(document_id: UUID, db: Session = Depends(get_db)):
    """Delete a document and cascade delete its chunks, facts, and relationships."""
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Find all fact IDs belonging to this document
    fact_ids = [f.id for f in doc.facts]
    if fact_ids:
        db.execute(
            delete(Relationship).where(
                (Relationship.fact_a_id.in_(fact_ids)) |
                (Relationship.fact_b_id.in_(fact_ids))
            )
        )

    db.delete(doc)
    db.commit()
    return {"message": f"Document '{doc.filename}' and its associated facts and relationships deleted."}


@router.post("/{document_id}/reprocess", response_model=UploadResponse, status_code=202)
def reprocess_document(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    background: bool = Query(True),
    db: Session = Depends(get_db),
):
    """Re-run the fact extraction and comparison pipeline for an existing document."""
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = UPLOAD_DIR / doc.filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Original PDF file no longer found on disk.")

    doc.status = "processing"
    db.commit()

    if background:
        background_tasks.add_task(run_pipeline_sync, doc.id, str(file_path))
        return UploadResponse(
            message="Reprocessing started in background.",
            document_id=doc.id,
            filename=doc.filename,
            status="processing",
        )
    else:
        run_pipeline_sync(doc.id, str(file_path))
        db.refresh(doc)
        fact_count = db.query(Fact).filter(Fact.document_id == doc.id).count()
        return UploadResponse(
            message="Reprocessing complete.",
            document_id=doc.id,
            filename=doc.filename,
            status=doc.status,
            facts_extracted=fact_count,
        )
