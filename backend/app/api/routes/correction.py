"""
TruthGuard Correction API Route.

POST /api/v1/correction
"""

from __future__ import annotations
from fastapi import APIRouter, status
from app.schemas.schemas import CorrectionRequest, CorrectionResponse
from app.services.correction.engine import CorrectionEngine

router = APIRouter(prefix="/correction", tags=["Correction"])
engine = CorrectionEngine()


@router.post("", response_model=CorrectionResponse, status_code=status.HTTP_200_OK)
async def correct_response_endpoint(request: CorrectionRequest) -> CorrectionResponse:
    """Generate evidence-grounded corrected response from claim verdicts."""
    return engine.correct_response(
        original_output=request.original_response,
        verdicts=request.claim_verdicts,
        domain=request.domain
    )
