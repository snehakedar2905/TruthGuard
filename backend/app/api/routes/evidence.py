"""
TruthGuard Evidence Search API Route.

POST /api/v1/evidence/search
POST /api/v1/evidence/sources
"""

from __future__ import annotations
import logging
from fastapi import APIRouter, HTTPException, status
from app.core.config import settings
from app.schemas.schemas import (
    ClaimSourcesResponse,
    EvidenceSearchRequest,
    EvidenceSearchResponse,
    ExternalSourceItem,
    ExternalSourcesRequest,
)
from app.services.retrieval.retriever import EvidenceRetrievalEngine
from app.services.retrieval.tavily_client import TavilyAPIError, TavilyConfigError

logger = logging.getLogger("truthlens.evidence")
router = APIRouter(prefix="/evidence", tags=["Evidence"])
retriever = EvidenceRetrievalEngine()


@router.post("/search", response_model=EvidenceSearchResponse, status_code=status.HTTP_200_OK)
async def search_evidence_endpoint(request: EvidenceSearchRequest) -> EvidenceSearchResponse:
    """Execute search for real web evidence via Tavily."""
    try:
        items = await retriever.search_evidence_async(
            query=request.query,
            claim_id=request.claim_id,
            top_k=request.top_k,
            min_similarity=request.min_similarity,
            temporal_filter_year=request.temporal_filter_year,
            use_tavily=True,
        )
    except TavilyConfigError as e:
        logger.error(f"[TruthLens] {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tavily API key is not configured",
        )
    except TavilyAPIError as e:
        logger.error(f"[TruthLens] {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="External source verification is temporarily unavailable",
        )

    return EvidenceSearchResponse(
        query=request.query,
        evidence=items,
        total_retrieved=len(items),
    )


@router.post("/sources", response_model=ClaimSourcesResponse, status_code=status.HTTP_200_OK)
async def get_external_sources_endpoint(request: ExternalSourcesRequest) -> ClaimSourcesResponse:
    """Retrieve actual external web sources from Tavily for a given claim."""
    if not retriever.tavily_client.is_configured() and not settings.mock_mode:
        logger.error("[TruthLens] TAVILY_API_KEY is not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tavily API key is not configured",
        )

    try:
        evidence = await retriever.search_evidence_async(
            query=request.claim,
            claim_id=request.claim_id,
            top_k=request.max_results,
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
            claim_id=request.claim_id,
            claim=request.claim,
            sources=sources,
        )
    except TavilyConfigError as e:
        logger.error(f"[TruthLens] {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tavily API key is not configured",
        )
    except TavilyAPIError as e:
        logger.error(f"[TruthLens] {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="External source verification is temporarily unavailable",
        )
    except Exception as e:
        logger.error(f"[TruthLens] Unexpected error retrieving sources: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="External source verification is temporarily unavailable",
        )
