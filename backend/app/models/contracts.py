from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Contract(Base):
    __tablename__ = "contracts"

    contract_id = Column(Integer, primary_key=True, autoincrement=True)
    internal_ref_no = Column(String(50), unique=True, nullable=True)
    file_name = Column(String(255), nullable=False)
    pdf_path = Column(Text, nullable=False)
    file_hash = Column(String(64), unique=True, nullable=False)
    country_code = Column(String(2), nullable=True)
    jurisdiction_state_city = Column(String(100), nullable=True)
    language = Column(String(20), nullable=True)
    execution_date = Column(Date, nullable=True)
    term_years = Column(Integer, nullable=True)
    expiry_date = Column(Date, nullable=True)
    is_exclusive = Column(Boolean, default=True)
    status = Column(String(20), default="processing")  # processing | processed | needs_review
    signature_present = Column(Boolean, nullable=True)
    stamp_present = Column(Boolean, nullable=True)
    upload_date = Column(DateTime, server_default=func.now())

    parties = relationship("ContractParty", back_populates="contract", cascade="all, delete-orphan")
    works = relationship("MusicalWork", back_populates="contract", cascade="all, delete-orphan")
    terms = relationship("ContractTerms", back_populates="contract", uselist=False, cascade="all, delete-orphan")
    intelligence = relationship("ContractIntelligence", back_populates="contract", uselist=False, cascade="all, delete-orphan")


class ContractParty(Base):
    __tablename__ = "contract_parties"

    party_id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(Integer, ForeignKey("contracts.contract_id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), nullable=True)
    legal_name = Column(String(255), nullable=True)
    representative_name = Column(String(255), nullable=True)
    id_type = Column(String(50), nullable=True)
    id_value = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)

    contract = relationship("Contract", back_populates="parties")


class MusicalWork(Base):
    __tablename__ = "musical_works"

    work_id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(Integer, ForeignKey("contracts.contract_id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=True)
    artist_performer = Column(String(255), nullable=True)
    lyricist = Column(String(255), nullable=True)
    isrc_code = Column(String(20), nullable=True)
    collection_society = Column(String(50), nullable=True)

    contract = relationship("Contract", back_populates="works")


class ContractTerms(Base):
    __tablename__ = "contract_terms"

    term_id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(Integer, ForeignKey("contracts.contract_id", ondelete="CASCADE"), nullable=False)
    remuneration_amount = Column(Numeric(15, 2), nullable=True)
    currency = Column(String(3), nullable=True)
    min_penalty_liquidated_damages = Column(Numeric(15, 2), nullable=True)
    delivery_deadline_days = Column(Integer, nullable=True)
    registration_deadline_days = Column(Integer, nullable=True)
    streaming_requirement_days = Column(Integer, nullable=True)

    contract = relationship("Contract", back_populates="terms")


class ContractIntelligence(Base):
    __tablename__ = "contract_intelligence"

    intel_id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(Integer, ForeignKey("contracts.contract_id", ondelete="CASCADE"), nullable=False)
    raw_text = Column(Text, nullable=True)
    summary_short = Column(Text, nullable=True)
    translated_text_en = Column(Text, nullable=True)
    embedding = Column(Vector(384), nullable=True)  # sentence-transformers all-MiniLM-L6-v2

    contract = relationship("Contract", back_populates="intelligence")
