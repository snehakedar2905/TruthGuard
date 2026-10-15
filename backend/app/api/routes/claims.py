"""
TruthGuard Claim Extraction & Verification Routes.

POST /api/v1/claims/extract
POST /api/v1/claims/verify
GET  /api/v1/claims/{claim_id}/sources
"""

from __future__ import annotations
import asyncio
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import validate_input_size
from app.models.database import ClaimRecord, get_db
from app.schemas.schemas import (
    ClaimExtractionRequest,
    ClaimExtractionResponse,
    ClaimSourcesResponse,
    ClaimVerifyRequest,
    ClaimVerifyResponse,
    ClaimVerdictResult,
    ExternalSourceItem,
)
from app.services.claim_extractor.extractor import ClaimExtractorService
from app.services.pipeline import TruthGuardPipeline
from app.services.retrieval.tavily_client import TavilyAPIError, TavilyConfigError

router = APIRouter(prefix="/claims", tags=["Claims"])
extractor = ClaimExtractorService()
pipeline = TruthGuardPipeline()


@router.post("/extract", response_model=ClaimExtractionResponse, status_code=status.HTTP_200_OK)
async def extract_claims_endpoint(request: ClaimExtractionRequest) -> ClaimExtractionResponse:
    """Decompose text into atomic propositions and annotate entities and temporal markers."""
    validate_input_size(request.text)
    claims = extractor.extract_claims(text=request.text, context=request.context)
    return ClaimExtractionResponse(
        claims=claims,
        total_claims=len(claims),
        extraction_method="hybrid_dependency_nlp",
    )


@router.post("/verify", response_model=ClaimVerifyResponse, status_code=status.HTTP_200_OK)
async def verify_claims_endpoint(request: ClaimVerifyRequest) -> ClaimVerifyResponse:
    """Run multi-signal verification across a list of pre-extracted atomic claims."""
    tasks = [
        pipeline._verify_single_claim(claim, request.domain, request.input_context)
        for claim in request.claims
    ]
    results: List[ClaimVerdictResult] = await asyncio.gather(*tasks)

    overall_confidence = round(
        sum(r.confidence for r in results) / max(1, len(results)),
        3,
    ) if results else 0.0

    return ClaimVerifyResponse(
        results=results,
        overall_confidence=overall_confidence,
    )


@router.get("/{claim_id}/sources", response_model=ClaimSourcesResponse, status_code=status.HTTP_200_OK)
async def get_claim_sources_endpoint(claim_id: str, db: Session = Depends(get_db)) -> ClaimSourcesResponse:
    """Retrieve actual external web sources (Tavily results) associated with a verified claim."""
    # 1. Look up claim in SQLite database
    claim_rec = db.query(ClaimRecord).filter(
        (ClaimRecord.id == claim_id) | (ClaimRecord.id.endswith(f"_{claim_id}"))
    ).first()

    if claim_rec and claim_rec.evidence_items:
        sources = [
            ExternalSourceItem(
                title=ev.title,
                url=ev.url,
                content=ev.content,
                score=ev.relevance_score,
                published_date=ev.publication_date,
                domain=ev.source,
            )
            for ev in claim_rec.evidence_items
        ]
        return ClaimSourcesResponse(
            claim_id=claim_id,
            claim=claim_rec.claim_text,
            sources=sources,
        )

    # 2. If not stored or queried dynamically, retrieve via Tavily
    query_text = claim_rec.claim_text if claim_rec else claim_id
    try:
        evidence = await pipeline.retriever.search_evidence_async(
            query=query_text,
            claim_id=claim_id,
            top_k=5,
            use_tavily=True,
        )
        sources = [
            ExternalSourceItem(
                title=ev.title,
                url=ev.url,
                content=ev.text,
                score=ev.relevance_score,
                published_date=ev.publication_date,
                domain=ev.source,
            )
            for ev in evidence
        ]
        return ClaimSourcesResponse(
            claim_id=claim_id,
            claim=query_text,
            sources=sources,
        )
    except TavilyConfigError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tavily API key is not configured",
        )
    except TavilyAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="External source verification is temporarily unavailable",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="External source verification is temporarily unavailable",
        )
