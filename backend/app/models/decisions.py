import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy import TIMESTAMP
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class CourtDecision(Base):
    __tablename__ = "court_decisions"
    __table_args__ = {"schema": "decisions"}

    id = Column(String(36), primary_key=True, default=_uuid)
    source_filename = Column(Text, nullable=True)

    court = Column(Text, nullable=True)
    judge = Column(Text, nullable=True)
    case_number = Column(Text, nullable=True)
    case_type = Column(Text, nullable=True)
    plaintiff = Column(Text, nullable=True)
    defendant = Column(Text, nullable=True)
    outcome = Column(Text, nullable=True)
    decision_date = Column(Date, nullable=True)

    full_text = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    monetary_award = Column(Numeric(15, 2), nullable=True)
    appeal_of = Column(Text, nullable=True)

    # processing_status mirrors the decisions.decisionstatus enum
    processing_status = Column(String(20), nullable=False, default="pending")
    is_ocr = Column(Boolean, nullable=False, default=False)
    ocr_confidence = Column(Float, nullable=True)
    extraction_error = Column(Text, nullable=True)

    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    embeddings = relationship("DecisionEmbedding", back_populates="decision", cascade="all, delete-orphan")
    arguments = relationship("DecisionArgument", back_populates="decision", cascade="all, delete-orphan")
    legal_refs = relationship("DecisionLegalRef", back_populates="decision", cascade="all, delete-orphan")
    categories = relationship("DecisionCategory", back_populates="decision", cascade="all, delete-orphan")


class DecisionEmbedding(Base):
    __tablename__ = "decision_embeddings"
    __table_args__ = {"schema": "decisions"}

    id = Column(String(36), primary_key=True, default=_uuid)
    decision_id = Column(String(36), ForeignKey("decisions.court_decisions.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    embedding = Column(Vector(384), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    decision = relationship("CourtDecision", back_populates="embeddings")


class DecisionCategory(Base):
    __tablename__ = "decision_categories"
    __table_args__ = {"schema": "decisions"}

    id = Column(String(36), primary_key=True, default=_uuid)
    decision_id = Column(String(36), ForeignKey("decisions.court_decisions.id", ondelete="CASCADE"), nullable=False)
    category = Column(Text, nullable=False)
    subcategory = Column(Text, nullable=False)

    decision = relationship("CourtDecision", back_populates="categories")


class DecisionArgument(Base):
    __tablename__ = "decision_arguments"
    __table_args__ = {"schema": "decisions"}

    id = Column(String(36), primary_key=True, default=_uuid)
    decision_id = Column(String(36), ForeignKey("decisions.court_decisions.id", ondelete="CASCADE"), nullable=False)
    side = Column(String(20), nullable=False)  # 'plaintiff' or 'defendant'
    argument = Column(Text, nullable=False)
    position = Column(Integer, nullable=False)

    decision = relationship("CourtDecision", back_populates="arguments")


class DecisionLegalRef(Base):
    __tablename__ = "decision_legal_refs"
    __table_args__ = {"schema": "decisions"}

    id = Column(String(36), primary_key=True, default=_uuid)
    decision_id = Column(String(36), ForeignKey("decisions.court_decisions.id", ondelete="CASCADE"), nullable=False)
    reference = Column(Text, nullable=False)

    decision = relationship("CourtDecision", back_populates="legal_refs")
