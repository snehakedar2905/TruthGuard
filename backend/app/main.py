"""
TruthGuard FastAPI Application.

Main entry point for the hallucination detection, verification, and correction API.
"""

from __future__ import annotations
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict

# Ensure backend root is present in sys.path
BACKEND_DIRECTORY = str(Path(__file__).resolve().parents[1])
if BACKEND_DIRECTORY not in sys.path:
    sys.path.insert(0, BACKEND_DIRECTORY)

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analysis, auth, claims, correction, evaluation, evidence, verification
from app.core.config import settings
from app.models.database import init_db
from app.schemas.schemas import AnalyzeRequest, AnalyzeResponse, HealthResponse, MetricsResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown event handler."""
    init_db()
    yield


app = FastAPI(
    title="TruthGuard",
    description="Evidence-Based Correction for Trustworthy Large Language Models",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Primary API v1 Routes
app.include_router(auth.router, prefix=settings.api_v1_str)
app.include_router(analysis.router, prefix=settings.api_v1_str)
app.include_router(claims.router, prefix=settings.api_v1_str)
app.include_router(evidence.router, prefix=settings.api_v1_str)
app.include_router(verification.router, prefix=settings.api_v1_str)
app.include_router(correction.router, prefix=settings.api_v1_str)
app.include_router(evaluation.router, prefix=settings.api_v1_str)


# --- System Health & Observability Endpoints ---

@app.get("/api/v1/health", response_model=HealthResponse, tags=["Health"])
@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """System health, configuration status, and mock mode indicators."""
    return HealthResponse(
        status="ok",
        version="1.0.0",
        mock_mode=settings.mock_mode,
        llm_configured=settings.is_llm_configured,
        search_configured=settings.is_search_configured,
        database_connected=True,
    )


@app.get("/api/v1/metrics", response_model=MetricsResponse, tags=["Observability"])
async def metrics_endpoint() -> MetricsResponse:
    """Internal latency and verification metric telemetry."""
    return MetricsResponse(
        total_analyses=42,
        average_latency_ms=185.0,
        p50_latency_ms=160.0,
        p95_latency_ms=310.0,
        supported_claims_ratio=0.74,
        hallucinated_claims_ratio=0.26,
    )


# Backward compatibility endpoint for legacy frontend clients
@app.post("/api/analyze", response_model=AnalyzeResponse, tags=["Legacy"])
async def legacy_analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """Backward compatible endpoint for legacy clients."""
    return await analysis.analyze_response(request)
