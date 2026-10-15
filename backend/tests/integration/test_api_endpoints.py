"""Integration tests for all TruthGuard FastAPI HTTP endpoints."""

import pytest
import httpx
from app.main import app


@pytest.mark.asyncio
async def test_health_endpoints():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        r1 = await client.get("/api/v1/health")
        assert r1.status_code == 200
        assert r1.json()["status"] == "ok"

        r2 = await client.get("/api/health")
        assert r2.status_code == 200
        assert "mock_mode" in r2.json()


@pytest.mark.asyncio
async def test_api_extract_claims():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        payload = {"text": "Google was founded in 1998. The Earth revolves around the Sun."}
        resp = await client.post("/api/v1/claims/extract", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_claims"] >= 2


@pytest.mark.asyncio
async def test_api_evidence_search():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        payload = {"query": "Albert Einstein theory of relativity", "top_k": 2}
        resp = await client.post("/api/v1/evidence/search", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["evidence"]) > 0


@pytest.mark.asyncio
async def test_api_nli_verify():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "claim": "Google was founded in 1998.",
            "evidence": "Google was founded in 1998 by Larry Page and Sergey Brin."
        }
        resp = await client.post("/api/v1/verification/nli", json=payload)
        assert resp.status_code == 200
        assert resp.json()["label"] == "SUPPORTED"


@pytest.mark.asyncio
async def test_api_kg_verify():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "claim": "Apollo 11 landed on the Moon in 1969.",
            "entities": ["Apollo 11", "Moon"]
        }
        resp = await client.post("/api/v1/verification/knowledge-graph", json=payload)
        assert resp.status_code == 200
        assert resp.json()["entity_exists"] is True


@pytest.mark.asyncio
async def test_api_consensus_verify():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "claim": "The Earth revolves around the Sun.",
            "evidence_snippets": ["The Earth revolves around the Sun."]
        }
        resp = await client.post("/api/v1/verification/consensus", json=payload)
        assert resp.status_code == 200
        assert resp.json()["consensus_score"] > 0.5


@pytest.mark.asyncio
async def test_api_full_analysis():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "llm_output": "Google was founded in 1999. The Earth revolves around the Sun.",
            "domain": "general",
            "apply_correction": True
        }
        resp = await client.post("/api/v1/analyze", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["claims"]) >= 2
        assert len(data["verdicts"]) >= 2
        assert "1998" in data["corrected_output"]


@pytest.mark.asyncio
async def test_api_auth_flow():
    import uuid
    unique_email = f"johndoe_{uuid.uuid4().hex[:8]}@example.com"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. Signup
        signup_payload = {
            "name": "John Doe",
            "country_code": "+1",
            "mobile_no": "555-234-5678",
            "email": unique_email,
            "password": "Password123!"
        }
        res_signup = await client.post("/api/v1/auth/signup", json=signup_payload)
        assert res_signup.status_code == 201
        data_signup = res_signup.json()
        assert "token" in data_signup
        assert data_signup["user"]["name"] == "John Doe"
        assert data_signup["user"]["country_code"] == "+1"
        assert data_signup["user"]["mobile_no"] == "5552345678"
        token = data_signup["token"]

        # 2. Verify Token
        res_verify = await client.get("/api/v1/auth/verify", headers={"Authorization": f"Bearer {token}"})
        assert res_verify.status_code == 200
        data_verify = res_verify.json()
        assert data_verify["user"]["email"] == unique_email
        assert data_verify["user"]["name"] == "John Doe"

        # 3. Update Profile
        res_profile = await client.put(
            "/api/v1/auth/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Johnathan Doe", "country_code": "+91", "mobile_no": "9876543210"}
        )
        assert res_profile.status_code == 200
        data_profile = res_profile.json()
        assert data_profile["user"]["name"] == "Johnathan Doe"
        assert data_profile["user"]["country_code"] == "+91"
        assert data_profile["user"]["mobile_no"] == "9876543210"

        # 4. Login
        login_payload = {
            "email": unique_email,
            "password": "Password123!"
        }
        res_login = await client.post("/api/v1/auth/login", json=login_payload)
        assert res_login.status_code == 200
        data_login = res_login.json()
        assert "token" in data_login
        assert data_login["user"]["name"] == "Johnathan Doe"


@pytest.mark.asyncio
async def test_api_contact_validation_flow():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. Reject alphabetic phone numbers
        res_bad = await client.post("/api/v1/auth/send-contact-otp", json={"country_code": "+1", "mobile_no": "555abc999"})
        assert res_bad.status_code == 400

        # 2. Valid contact number OTP dispatch
        res_send = await client.post("/api/v1/auth/send-contact-otp", json={"country_code": "+1", "mobile_no": "5551234567"})
        assert res_send.status_code == 200
        data_send = res_send.json()
        assert "otp" in data_send
        otp = data_send["otp"]

        # 3. Verify OTP
        res_verify = await client.post(
            "/api/v1/auth/verify-contact-otp",
            json={"country_code": "+1", "mobile_no": "5551234567", "otp": otp}
        )
        assert res_verify.status_code == 200
        assert res_verify.json()["verified"] is True

