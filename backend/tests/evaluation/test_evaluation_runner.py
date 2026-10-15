"""Evaluation suite test runner for automated benchmarking."""

import pytest
import httpx
from app.main import app


@pytest.mark.asyncio
async def test_evaluation_runner_executes_benchmark():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/evaluation/run", json={"dataset_name": "test_golden_set"})
        assert resp.status_code == 200
        data = resp.json()

        assert "metrics" in data
        metrics = data["metrics"]
        assert metrics["total_samples"] >= 5
        assert metrics["claim_extraction_f1"] > 0.0
        assert metrics["hallucination_detection_f1"] > 0.0
        assert metrics["verification_accuracy"] > 0.0
        assert metrics["p50_latency_ms"] >= 0.0
        assert "domain_breakdown" in data
