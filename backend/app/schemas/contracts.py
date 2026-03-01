from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel


class ContractPartyOut(BaseModel):
    party_id: int
    role: Optional[str]
    legal_name: Optional[str]
    representative_name: Optional[str]
    id_type: Optional[str]
    id_value: Optional[str]
    address: Optional[str]
    signing_status: Optional[str]  # none | signature_only | stamp_only | signature_and_stamp

    class Config:
        from_attributes = True


class MusicalWorkOut(BaseModel):
    work_id: int
    title: Optional[str]
    artist_performer: Optional[str]
    lyricist: Optional[str]
    isrc_code: Optional[str]
    collection_society: Optional[str]

    class Config:
        from_attributes = True


class ContractTermsOut(BaseModel):
    term_id: int
    remuneration_amount: Optional[Decimal]
    currency: Optional[str]
    min_penalty_liquidated_damages: Optional[Decimal]
    delivery_deadline_days: Optional[int]
    registration_deadline_days: Optional[int]
    streaming_requirement_days: Optional[int]

    class Config:
        from_attributes = True


class ContractIntelligenceOut(BaseModel):
    intel_id: int
    summary_short: Optional[str]
    translated_text_en: Optional[str]

    class Config:
        from_attributes = True


class ContractListItem(BaseModel):
    contract_id: int
    internal_ref_no: Optional[str]
    file_name: str
    country_code: Optional[str]
    language: Optional[str]
    execution_date: Optional[date]
    expiry_date: Optional[date]
    status: Optional[str]
    upload_date: Optional[datetime]

    class Config:
        from_attributes = True


class ContractDetail(BaseModel):
    contract_id: int
    internal_ref_no: Optional[str]
    file_name: str
    country_code: Optional[str]
    jurisdiction_state_city: Optional[str]
    language: Optional[str]
    execution_date: Optional[date]
    term_years: Optional[int]
    expiry_date: Optional[date]
    is_exclusive: Optional[bool]
    status: Optional[str]
    upload_date: Optional[datetime]
    parties: List[ContractPartyOut] = []
    works: List[MusicalWorkOut] = []
    terms: Optional[ContractTermsOut] = None
    intelligence: Optional[ContractIntelligenceOut] = None

    class Config:
        from_attributes = True


class SimilarContract(BaseModel):
    contract_id: int
    internal_ref_no: Optional[str]
    file_name: str
    similarity: float


class ChatMessage(BaseModel):
    message: str
    history: List[dict] = []


class ChatResponse(BaseModel):
    answer: str
    sql: Optional[str] = None
    results: Optional[list] = None


class CaseSummaryRequest(BaseModel):
    summary: str


class SummaryMatchResult(BaseModel):
    id: str
    source_filename: Optional[str]
    court: Optional[str]
    case_number: Optional[str]
    case_type: Optional[str]
    plaintiff: Optional[str]
    defendant: Optional[str]
    outcome: Optional[str]
    similarity: Optional[float] = None
    matched_categories: Optional[List[str]] = None
