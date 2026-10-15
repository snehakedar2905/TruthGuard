"""Failure mode and edge-case resilience tests."""

import pytest
import httpx
from app.main import app
from app.schemas.schemas import AnalyzeRequest, DomainType
from app.services.pipeline import TruthGuardPipeline


@pytest.mark.asyncio
async def test_empty_input_handling():
    pipeline = TruthGuardPipeline()
    req = AnalyzeRequest(llm_output="", domain=DomainType.GENERAL)
    res = await pipeline.run_pipeline(req)

    assert len(res.claims) == 0
    assert len(res.verdicts) == 0
    assert res.corrected_output == ""


@pytest.mark.asyncio
async def test_excessive_payload_rejection():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Generate huge input exceeding size limit
        huge_text = "Google was founded. " * 2000
        resp = await client.post("/api/v1/analyze", json={"llm_output": huge_text})
        assert resp.status_code == 413


@pytest.mark.asyncio
async def test_completely_unknown_claim_marks_unverifiable():
    pipeline = TruthGuardPipeline()
    req = AnalyzeRequest(
        llm_output="The underwater kingdom of Zylar was founded by Zephyrus in 1312.",
        domain=DomainType.GENERAL,
        apply_correction=True
    )
    res = await pipeline.run_pipeline(req)

    assert len(res.claims) >= 1
    unverifiable_verdict = res.verdicts[0]
    assert unverifiable_verdict.verdict in ("UNVERIFIABLE", "ENTITY_UNSUPPORTED")
    assert "[Unverified:" in res.corrected_output
