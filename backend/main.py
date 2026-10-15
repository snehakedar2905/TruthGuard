"""
TruthGuard FastAPI Application Entry Point.

Exposes `app` so the server can be started with either:
    python -m uvicorn main:app --reload
or
    python -m uvicorn app.main:app --reload
"""

from app.main import app

__all__ = ["app"]
