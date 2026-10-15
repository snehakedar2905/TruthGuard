"""Integration tests for the full TruthGuard verification pipeline."""

import pytest
from app.schemas.schemas import AnalyzeRequest, DomainType, VerdictType
from app.services.pipeline import TruthGuardPipeline


@pytest.mark.asyncio
async def test_pipeline_end_to_end_contradiction_and_correction():
    pipeline = TruthGuardPipeline()
    req = AnalyzeRequest(
        llm_output="Google was founded in 1999. The Earth revolves around the Sun.",
        domain=DomainType.GENERAL,
        apply_correction=True
    )

    res = await pipeline.run_pipeline(req)

    assert len(res.claims) >= 2
    assert len(res.verdicts) >= 2
    assert len(res.evidence) > 0

    # Google 1999 should be marked contradicted or temporally inconsistent
    google_verdict = next((v for v in res.verdicts if "1999" in v.claim_text or "Google" in v.claim_text), None)
    assert google_verdict is not None
    assert google_verdict.verdict in (VerdictType.CONTRADICTED, VerdictType.TEMPORALLY_INCONSISTENT)

    # Earth claim should be supported
    earth_verdict = next((v for v in res.verdicts if "Earth" in v.claim_text), None)
    assert earth_verdict is not None
    assert earth_verdict.verdict == VerdictType.SUPPORTED

    # Corrected output should fix the 1999 to 1998
    assert "1998" in res.corrected_output
    assert res.processing_time_ms > 0
