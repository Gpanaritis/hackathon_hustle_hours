from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
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


@router.delete("/{decision_id}", status_code=204)
def delete_decision(decision_id: str, db: Session = Depends(get_db)):
    decision = db.query(CourtDecision).filter(CourtDecision.id == decision_id).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found.")

    # Remove file from disk if it exists
    from pathlib import Path as _Path
    source = decision.source_filename or ""
    ext = _Path(source).suffix.lower() if source else ".pdf"
    file_path = Path(settings.storage_path).parent / "decisions" / f"{decision_id}{ext}"
    if file_path.exists():
        file_path.unlink()

    db.delete(decision)
    db.commit()


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

    query_embedding = decision.embeddings[0].embedding

    if query_embedding is None:
        raise HTTPException(status_code=422, detail="No embeddings available for this decision.")

    from sqlalchemy import text as sa_text
    vec_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
    rows = db.execute(
        sa_text("""
            SELECT decision_id,
                   embedding <=> CAST(:query_vec AS vector(384)) AS distance
            FROM decisions.decision_embeddings
            WHERE decision_id != :did
            ORDER BY distance
            LIMIT 5
        """),
        {"query_vec": vec_str, "did": decision_id},
    ).fetchall()

    similar = []
    for row in rows:
        d = db.query(CourtDecision).filter(CourtDecision.id == row.decision_id).first()
        if d:
            similar.append(SimilarDecision(
                id=d.id,
                source_filename=d.source_filename,
                court=d.court,
                case_number=d.case_number,
                similarity=round((1 - row.distance) * 100, 1),
            ))
    return similar
