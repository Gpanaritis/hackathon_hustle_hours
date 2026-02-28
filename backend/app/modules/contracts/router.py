import os
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.contracts import Contract, ContractIntelligence, ContractParty
from app.modules.contracts.processor import process_contract
from app.schemas.contracts import ContractDetail, ContractListItem, SimilarContract

router = APIRouter()


@router.post("/upload", response_model=ContractDetail, status_code=201)
def upload_contract(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    file_bytes = file.file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        contract = process_contract(file_bytes, file.filename, db)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))

    db.refresh(contract)
    return contract


@router.get("", response_model=List[ContractListItem])
def list_contracts(
    country_code: Optional[str] = Query(None),
    party_name: Optional[str] = Query(None),
    expiring_this_year: Optional[bool] = Query(None),
    missing_signature: Optional[bool] = Query(None),
    missing_stamp: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    from sqlalchemy import extract
    from datetime import date

    q = db.query(Contract)

    if country_code:
        q = q.filter(Contract.country_code == country_code.upper())

    if party_name:
        q = q.join(ContractParty).filter(
            ContractParty.legal_name.ilike(f"%{party_name}%")
        )

    if expiring_this_year:
        current_year = date.today().year
        q = q.filter(extract("year", Contract.expiry_date) == current_year)

    if missing_signature:
        q = q.filter(Contract.signature_present == False)

    if missing_stamp:
        q = q.filter(Contract.stamp_present == False)

    offset = (page - 1) * page_size
    contracts = q.order_by(Contract.upload_date.desc()).offset(offset).limit(page_size).all()
    return contracts


@router.get("/{contract_id}", response_model=ContractDetail)
def get_contract(contract_id: int, db: Session = Depends(get_db)):
    contract = db.query(Contract).filter(Contract.contract_id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found.")
    return contract


@router.get("/{contract_id}/download")
def download_contract(contract_id: int, db: Session = Depends(get_db)):
    contract = db.query(Contract).filter(Contract.contract_id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found.")

    pdf_path = Path(contract.pdf_path)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found on disk.")

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=contract.file_name,
    )


@router.get("/{contract_id}/similar", response_model=List[SimilarContract])
def similar_contracts(contract_id: int, db: Session = Depends(get_db)):
    contract = db.query(Contract).filter(Contract.contract_id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found.")

    if not contract.intelligence or contract.intelligence.embedding is None:
        raise HTTPException(status_code=422, detail="Embedding not available for this contract.")

    embedding = contract.intelligence.embedding

    # pgvector cosine similarity — lower distance = more similar
    results = (
        db.query(
            ContractIntelligence.contract_id,
            ContractIntelligence.embedding.cosine_distance(embedding).label("distance"),
        )
        .filter(ContractIntelligence.contract_id != contract_id)
        .filter(ContractIntelligence.embedding.isnot(None))
        .order_by("distance")
        .limit(5)
        .all()
    )

    similar = []
    for row in results:
        c = db.query(Contract).filter(Contract.contract_id == row.contract_id).first()
        if c:
            similar.append(
                SimilarContract(
                    contract_id=c.contract_id,
                    internal_ref_no=c.internal_ref_no,
                    file_name=c.file_name,
                    similarity=round((1 - row.distance) * 100, 1),
                )
            )
    return similar
