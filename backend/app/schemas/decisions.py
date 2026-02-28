from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel


class DecisionArgumentOut(BaseModel):
    id: str
    side: str  # 'plaintiff' or 'defendant'
    argument: str
    position: int

    class Config:
        from_attributes = True


class DecisionLegalRefOut(BaseModel):
    id: str
    reference: str

    class Config:
        from_attributes = True


class DecisionListItem(BaseModel):
    id: str
    source_filename: Optional[str]
    court: Optional[str]
    judge: Optional[str]
    case_number: Optional[str]
    case_type: Optional[str]
    plaintiff: Optional[str]
    defendant: Optional[str]
    outcome: Optional[str]
    decision_date: Optional[date]
    monetary_award: Optional[Decimal]
    processing_status: str
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class DecisionDetail(BaseModel):
    id: str
    source_filename: Optional[str]
    court: Optional[str]
    judge: Optional[str]
    case_number: Optional[str]
    case_type: Optional[str]
    plaintiff: Optional[str]
    defendant: Optional[str]
    outcome: Optional[str]
    decision_date: Optional[date]
    full_text: Optional[str]
    summary: Optional[str]
    monetary_award: Optional[Decimal]
    appeal_of: Optional[str]
    processing_status: str
    is_ocr: bool
    ocr_confidence: Optional[float]
    extraction_error: Optional[str]
    created_at: Optional[datetime]
    arguments: List[DecisionArgumentOut] = []
    legal_refs: List[DecisionLegalRefOut] = []

    class Config:
        from_attributes = True


class SimilarDecision(BaseModel):
    id: str
    source_filename: Optional[str]
    court: Optional[str]
    case_number: Optional[str]
    similarity: float
