"""
TruthGuard SQLAlchemy Database Models.

Stores analyses, decomposed claims, retrieved evidence, multi-signal verification results,
and applied corrections with full relational integrity and JSON serialization.
"""

from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from app.core.config import settings

Base = declarative_base()


def generate_uuid() -> str:
    return str(uuid.uuid4())


class AnalysisRecord(Base):
    """Stores the overarching analysis session and metadata."""

    __tablename__ = "analyses"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    input_context = Column(Text, nullable=True)
    original_output = Column(Text, nullable=False)
    corrected_output = Column(Text, nullable=True)
    domain = Column(String(50), default="general")
    language = Column(String(10), default="en")
    overall_confidence = Column(Float, default=0.0)
    processing_time_ms = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    claims = relationship("ClaimRecord", back_populates="analysis", cascade="all, delete-orphan")
    corrections = relationship("CorrectionRecord", back_populates="analysis", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "input_context": self.input_context,
            "original_output": self.original_output,
            "corrected_output": self.corrected_output,
            "domain": self.domain,
            "language": self.language,
            "overall_confidence": self.overall_confidence,
            "processing_time_ms": self.processing_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ClaimRecord(Base):
    """Stores individual atomic claims extracted from the LLM output."""

    __tablename__ = "claims"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    analysis_id = Column(String(36), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    claim_text = Column(Text, nullable=False)
    claim_type = Column(String(50), default="factual")
    entities_json = Column(Text, default="[]")
    temporal_expressions_json = Column(Text, default="[]")
    claim_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    analysis = relationship("AnalysisRecord", back_populates="claims")
    evidence_items = relationship("EvidenceRecord", back_populates="claim", cascade="all, delete-orphan")
    verification = relationship("VerificationRecord", back_populates="claim", uselist=False, cascade="all, delete-orphan")

    @property
    def entities(self) -> List[str]:
        return json.loads(self.entities_json) if self.entities_json else []

    @entities.setter
    def entities(self, value: List[str]) -> None:
        self.entities_json = json.dumps(value)

    @property
    def temporal_expressions(self) -> List[str]:
        return json.loads(self.temporal_expressions_json) if self.temporal_expressions_json else []

    @temporal_expressions.setter
    def temporal_expressions(self, value: List[str]) -> None:
        self.temporal_expressions_json = json.dumps(value)


class EvidenceRecord(Base):
    """Stores evidence passages retrieved for specific claims."""

    __tablename__ = "evidence"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    claim_id = Column(String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    source = Column(String(255), nullable=False)
    url = Column(String(1024), nullable=True)
    title = Column(String(512), nullable=True)
    content = Column(Text, nullable=False)
    relevance_score = Column(Float, default=0.0)
    authority_score = Column(Float, default=1.0)
    publication_date = Column(String(50), nullable=True)
    retrieved_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    claim = relationship("ClaimRecord", back_populates="evidence_items")


class VerificationRecord(Base):
    """Stores the multi-signal score breakdown and final verdict."""

    __tablename__ = "verification_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    claim_id = Column(String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False)
    nli_score = Column(Float, default=0.0)
    retrieval_score = Column(Float, default=0.0)
    kg_score = Column(Float, default=0.0)
    consensus_score = Column(Float, default=0.0)
    credibility_score = Column(Float, default=0.0)
    temporal_score = Column(Float, default=0.0)
    final_score = Column(Float, default=0.0)
    verdict = Column(String(50), nullable=False)
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    claim = relationship("ClaimRecord", back_populates="verification")


class CorrectionRecord(Base):
    """Stores claim-level modifications and rationales."""

    __tablename__ = "corrections"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    analysis_id = Column(String(36), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    original_claim = Column(Text, nullable=False)
    corrected_claim = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    evidence_ids_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    analysis = relationship("AnalysisRecord", back_populates="corrections")


class UserRecord(Base):
    """User account entity storing profile, country code, contact number, and credentials."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    country_code = Column(String(10), default="+1")
    mobile_no = Column(String(30), nullable=True)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "country_code": self.country_code or "+1",
            "mobile_no": self.mobile_no or "",
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Engine and Session initialization
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create all database tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


# Auto-initialize database tables
init_db()


def get_db():
    """FastAPI database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
