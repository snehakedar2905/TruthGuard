"""
TruthGuard Analysis API Routes.

Primary endpoint: POST /api/v1/analyze
Retrieval of prior sessions: GET /api/v1/analysis/{analysis_id}
"""

from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import validate_input_size
from app.models.database import AnalysisRecord, get_db
from app.schemas.schemas import AnalyzeRequest, AnalyzeResponse
from app.services.pipeline import TruthGuardPipeline

router = APIRouter(tags=["Analysis"])
pipeline = TruthGuardPipeline()


@router.post("/analyze", response_model=AnalyzeResponse, status_code=status.HTTP_200_OK)
async def analyze_response(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Run end-to-end hallucination detection, multi-signal verification,
    and evidence-based correction on LLM output.
    """
    validate_input_size(request.llm_output)
    if request.input_context:
        validate_input_size(request.input_context)

    return await pipeline.run_pipeline(request)


@router.get("/analysis/{analysis_id}", status_code=status.HTTP_200_OK)
async def get_analysis_by_id(analysis_id: str, db: Session = Depends(get_db)):
    """Retrieve details and claims for a previous analysis session."""
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == analysis_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis session '{analysis_id}' not found."
        )
    return {
        "analysis": record.to_dict(),
        "claims_count": len(record.claims),
        "claims": [
            {
                "id": c.id,
                "text": c.claim_text,
                "type": c.claim_type,
                "entities": c.entities,
                "temporals": c.temporal_expressions,
                "verification": {
                    "verdict": c.verification.verdict if c.verification else None,
                    "confidence": c.verification.final_score if c.verification else None,
                    "explanation": c.verification.explanation if c.verification else None
                } if c.verification else None
            }
            for c in record.claims
        ]
    }
