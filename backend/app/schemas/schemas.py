"""
TruthGuard Pydantic v2 Request & Response Schemas.

Comprehensive validation models for all API endpoints, modules, and pipeline stages.
"""

from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, HttpUrl


class HallucinationType(str, Enum):
    FACTUAL = "factual"
    FAITHFUL = "faithful"
    LOGICAL = "logical"
    TEMPORAL = "temporal"
    ENTITY = "entity"
    NONE = "none"


class VerdictType(str, Enum):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNVERIFIABLE = "UNVERIFIABLE"
    CONTEXT_INCONSISTENT = "CONTEXT_INCONSISTENT"
    LOGICALLY_INCONSISTENT = "LOGICALLY_INCONSISTENT"
    TEMPORALLY_INCONSISTENT = "TEMPORALLY_INCONSISTENT"
    ENTITY_UNSUPPORTED = "ENTITY_UNSUPPORTED"


class DomainType(str, Enum):
    GENERAL = "general"
    HEALTHCARE = "healthcare"
    LEGAL = "legal"
    SCIENTIFIC = "scientific"
    EDUCATION = "education"
    JOURNALISM = "journalism"


# --- Claim Extraction Schemas ---

class ClaimExtractionRequest(BaseModel):
    text: str = Field(..., description="Text from which to extract atomic factual claims")
    context: Optional[str] = Field(None, description="Optional grounding source context")
    language: str = Field(default="en", description="ISO language code")


class ExtractedClaim(BaseModel):
    claim_id: str
    text: str
    type: HallucinationType = HallucinationType.FACTUAL
    entities: List[str] = Field(default_factory=list)
    temporal_expressions: List[str] = Field(default_factory=list)
    char_start: Optional[int] = None
    char_end: Optional[int] = None


class ClaimExtractionResponse(BaseModel):
    claims: List[ExtractedClaim]
    total_claims: int
    extraction_method: str = "hybrid_dependency_nlp"


# --- Evidence Schemas ---

class EvidenceItem(BaseModel):
    evidence_id: str
    claim_id: Optional[str] = None
    source: str
    url: Optional[str] = None
    title: Optional[str] = None
    text: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    authority_score: float = Field(default=1.0, ge=0.0, le=1.0)
    publication_date: Optional[str] = None
    retrieved_at: Optional[str] = None
    temporal_validity: bool = True
    source_type: str = "local"


class EvidenceSearchRequest(BaseModel):
    query: str
    claim_id: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=20)
    min_similarity: float = Field(default=0.3, ge=0.0, le=1.0)
    temporal_filter_year: Optional[int] = None


class EvidenceSearchResponse(BaseModel):
    query: str
    evidence: List[EvidenceItem]
    total_retrieved: int


# --- Multi-Signal Verification Schemas ---

class NLIVerifyRequest(BaseModel):
    claim: str
    evidence: str


class NLIVerifyResponse(BaseModel):
    entailment: float = Field(ge=0.0, le=1.0)
    neutral: float = Field(ge=0.0, le=1.0)
    contradiction: float = Field(ge=0.0, le=1.0)
    label: str


class KGVerifyRequest(BaseModel):
    claim: str
    entities: Optional[List[str]] = None


class KGVerifyResponse(BaseModel):
    entity_exists: bool
    relationship_exists: bool
    knowledge_graph_confidence: float = Field(ge=0.0, le=1.0)
    matched_triples: List[Dict[str, Any]] = Field(default_factory=list)


class ConsensusVerifyRequest(BaseModel):
    claim: str
    evidence_snippets: List[str] = Field(default_factory=list)


class ConsensusVerifyResponse(BaseModel):
    consensus_score: float = Field(ge=0.0, le=1.0)
    model_votes: Dict[str, str] = Field(default_factory=dict)
    summary: str


class VerificationSignals(BaseModel):
    nli: float = Field(default=0.0, ge=0.0, le=1.0)
    retrieval: float = Field(default=0.0, ge=0.0, le=1.0)
    knowledge_graph: float = Field(default=0.0, ge=0.0, le=1.0)
    credibility: float = Field(default=0.0, ge=0.0, le=1.0)
    consensus: float = Field(default=0.0, ge=0.0, le=1.0)
    temporal: float = Field(default=1.0, ge=0.0, le=1.0)


class ClaimVerdictResult(BaseModel):
    claim_id: str
    claim_text: str
    verdict: VerdictType
    confidence: float = Field(ge=0.0, le=1.0)
    hallucination_type: Optional[HallucinationType] = None
    signals: VerificationSignals
    evidence: List[EvidenceItem] = Field(default_factory=list)
    explanation: str


class ClaimVerifyRequest(BaseModel):
    claims: List[ExtractedClaim]
    domain: DomainType = DomainType.GENERAL
    input_context: Optional[str] = None


class ClaimVerifyResponse(BaseModel):
    results: List[ClaimVerdictResult]
    overall_confidence: float


# --- Correction Schemas ---

class CorrectionItem(BaseModel):
    claim_id: str
    original_claim: str
    corrected_claim: str
    reason: str
    evidence_ids: List[str] = Field(default_factory=list)
    action: str = "corrected"  # "preserved", "corrected", "flagged_unverifiable", "removed"


class CorrectionRequest(BaseModel):
    original_response: str
    claim_verdicts: List[ClaimVerdictResult]
    domain: DomainType = DomainType.GENERAL


class CorrectionResponse(BaseModel):
    original_output: str
    corrected_output: str
    corrections: List[CorrectionItem]
    preserved_claims_count: int
    corrected_claims_count: int
    unverifiable_claims_count: int


# --- Main Analysis Schema ---

class AnalyzeRequest(BaseModel):
    input_context: Optional[str] = Field(None, description="Optional source or reference context")
    llm_output: str = Field(..., description="LLM-generated text to analyze")
    domain: DomainType = DomainType.GENERAL
    language: str = "en"
    verify_external: bool = True
    apply_correction: bool = True


class AnalyzeResponse(BaseModel):
    analysis_id: str
    original_output: str
    overall_score: float
    domain: str
    claims: List[ExtractedClaim]
    verdicts: List[ClaimVerdictResult]
    corrected_output: str
    corrections: List[CorrectionItem]
    evidence: List[EvidenceItem]
    processing_time_ms: float
    is_mock: bool = False


# --- Evaluation Schemas ---

class EvaluationRunRequest(BaseModel):
    dataset_name: str = "default_benchmark"
    domain_filter: Optional[str] = None


class EvaluationMetrics(BaseModel):
    claim_extraction_f1: float
    hallucination_detection_f1: float
    verification_accuracy: float
    correction_accuracy: float
    false_positive_rate: float
    false_negative_rate: float
    p50_latency_ms: float
    p95_latency_ms: float
    total_samples: int


class EvaluationRunResponse(BaseModel):
    run_id: str
    dataset_name: str
    metrics: EvaluationMetrics
    domain_breakdown: Dict[str, Dict[str, float]]
    timestamp: str


# --- Health & Observability Schemas ---

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    mock_mode: bool
    llm_configured: bool
    search_configured: bool
    database_connected: bool


class MetricsResponse(BaseModel):
    total_analyses: int
    average_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    supported_claims_ratio: float
    hallucinated_claims_ratio: float


# --- External Sources Schemas ---

class ExternalSourceItem(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    content: Optional[str] = None
    score: Optional[float] = None
    published_date: Optional[str] = None
    domain: Optional[str] = None


class ClaimSourcesResponse(BaseModel):
    claim_id: Optional[str] = None
    claim: str
    sources: List[ExternalSourceItem]


class ExternalSourcesRequest(BaseModel):
    claim: str
    claim_id: Optional[str] = None
    max_results: int = Field(default=5, ge=1, le=10)
