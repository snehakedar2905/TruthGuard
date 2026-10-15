"""
TruthGuard Modular Verification API Routes.

POST /api/v1/verification/nli
POST /api/v1/verification/knowledge-graph
POST /api/v1/verification/consensus
"""

from __future__ import annotations
from fastapi import APIRouter, status

from app.schemas.schemas import (
    ConsensusVerifyRequest,
    ConsensusVerifyResponse,
    KGVerifyRequest,
    KGVerifyResponse,
    NLIVerifyRequest,
    NLIVerifyResponse,
)
from app.services.consensus.consensus import CrossModelConsensusService
from app.services.knowledge_graph.validator import KnowledgeGraphValidator
from app.services.nli.verifier import NLIVerificationService

router = APIRouter(prefix="/verification", tags=["Verification"])
nli_service = NLIVerificationService()
kg_validator = KnowledgeGraphValidator()
consensus_service = CrossModelConsensusService()


@router.post("/nli", response_model=NLIVerifyResponse, status_code=status.HTTP_200_OK)
async def verify_nli_endpoint(request: NLIVerifyRequest) -> NLIVerifyResponse:
    """Natural Language Inference premise-hypothesis scoring."""
    return nli_service.verify_pair(claim=request.claim, evidence=request.evidence)


@router.post("/knowledge-graph", response_model=KGVerifyResponse, status_code=status.HTTP_200_OK)
async def verify_kg_endpoint(request: KGVerifyRequest) -> KGVerifyResponse:
    """Validate claim facts against structured knowledge graph triples."""
    return kg_validator.validate_claim(claim_text=request.claim, entities=request.entities)


@router.post("/consensus", response_model=ConsensusVerifyResponse, status_code=status.HTTP_200_OK)
async def verify_consensus_endpoint(request: ConsensusVerifyRequest) -> ConsensusVerifyResponse:
    """Cross-model consensus ensemble agreement scoring."""
    return consensus_service.verify_consensus(claim=request.claim, evidence_snippets=request.evidence_snippets)
