from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.decisions import CourtDecision, DecisionEmbedding
from app.modules.decisions.processor import process_decision, process_decision_from_text
from app.schemas.decisions import DecisionDetail, DecisionListItem, SimilarDecision

router = APIRouter()


class TextDecisionBody(BaseModel):
    text: str
    label: str = ""


@router.post("/from-text", response_model=DecisionDetail, status_code=201)
def create_decision_from_text(
    body: TextDecisionBody,
    db: Session = Depends(get_db),
):
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Text body is empty.")

    try:
        decision = process_decision_from_text(body.text, body.label, db)
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))

    db.refresh(decision)
    return decision


@router.post("/upload", response_model=DecisionDetail, status_code=201)
def upload_decision(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith((".pdf", ".txt")):
        raise HTTPException(status_code=400, detail="Only PDF and TXT files are accepted.")

    file_bytes = file.file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        decision = process_decision(file_bytes, file.filename, db)
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))

    db.refresh(decision)
    return decision


@router.get("", response_model=List[DecisionListItem])
def list_decisions(
    court: Optional[str] = Query(None),
    judge: Optional[str] = Query(None),
    case_type: Optional[str] = Query(None),
    outcome: Optional[str] = Query(None),
    plaintiff: Optional[str] = Query(None),
    defendant: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(CourtDecision)

    if court:
        q = q.filter(CourtDecision.court.ilike(f"%{court}%"))
    if judge:
        q = q.filter(CourtDecision.judge.ilike(f"%{judge}%"))
    if case_type:
        q = q.filter(CourtDecision.case_type.ilike(f"%{case_type}%"))
    if outcome:
        q = q.filter(CourtDecision.outcome.ilike(f"%{outcome}%"))
    if plaintiff:
        q = q.filter(CourtDecision.plaintiff.ilike(f"%{plaintiff}%"))
    if defendant:
        q = q.filter(CourtDecision.defendant.ilike(f"%{defendant}%"))

    offset = (page - 1) * page_size
    return q.order_by(CourtDecision.created_at.desc()).offset(offset).limit(page_size).all()


@router.get("/{decision_id}", response_model=DecisionDetail)
def get_decision(decision_id: str, db: Session = Depends(get_db)):
    decision = db.query(CourtDecision).filter(CourtDecision.id == decision_id).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found.")
    return decision


@router.get("/{decision_id}/download")
def download_decision(decision_id: str, db: Session = Depends(get_db)):
    decision = db.query(CourtDecision).filter(CourtDecision.id == decision_id).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found.")

    from pathlib import Path as _Path
    source = decision.source_filename or ""
    ext = _Path(source).suffix.lower() if source else ".pdf"
    file_path = Path(settings.storage_path).parent / "decisions" / f"{decision_id}{ext}"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk.")

    media_type = "text/plain" if ext == ".txt" else "application/pdf"
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=source or f"{decision_id}{ext}",
    )


@router.get("/{decision_id}/similar", response_model=List[SimilarDecision])
def similar_decisions(decision_id: str, db: Session = Depends(get_db)):
    decision = db.query(CourtDecision).filter(CourtDecision.id == decision_id).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found.")

    if not decision.embeddings:
        raise HTTPException(status_code=422, detail="No embeddings available for this decision.")

    # Average the chunk embeddings to get a document-level vector
    avg_embedding = db.query(
        func.avg(DecisionEmbedding.embedding)
    ).filter(DecisionEmbedding.decision_id == decision_id).scalar()

    if avg_embedding is None:
        raise HTTPException(status_code=422, detail="No embeddings available for this decision.")

    # Find closest documents by averaging their chunk embeddings and comparing
    results = (
        db.query(
            DecisionEmbedding.decision_id,
            func.avg(DecisionEmbedding.embedding.cosine_distance(avg_embedding)).label("avg_distance"),
        )
        .filter(DecisionEmbedding.decision_id != decision_id)
        .group_by(DecisionEmbedding.decision_id)
        .order_by("avg_distance")
        .limit(5)
        .all()
    )

    similar = []
    for row in results:
        d = db.query(CourtDecision).filter(CourtDecision.id == row.decision_id).first()
        if d:
            similar.append(SimilarDecision(
                id=d.id,
                source_filename=d.source_filename,
                court=d.court,
                case_number=d.case_number,
                similarity=round((1 - row.avg_distance) * 100, 1),
            ))
    return similar
