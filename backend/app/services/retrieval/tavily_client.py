"""
TruthGuard / TruthLens Tavily Search Client.

Interacts with the official Tavily API endpoint:
POST https://api.tavily.com/search

Supports search execution, query reformulation, rate limit handling,
and safe logging without exposing secrets.
"""

from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
import httpx

from app.core.config import settings

logger = logging.getLogger("truthlens.tavily")

TAVILY_API_URL = "https://api.tavily.com/search"


class TavilyConfigError(Exception):
    """Raised when TAVILY_API_KEY is missing or invalid."""
    pass


class TavilyAPIError(Exception):
    """Raised when the Tavily API fails or times out."""
    pass


class TavilySearchClient:
    """Production client for real Tavily Web Search."""

    def __init__(self, api_key: Optional[str] = None, timeout: float = 12.0) -> None:
        self._api_key = api_key
        self.timeout = timeout

    @property
    def api_key(self) -> Optional[str]:
        return self._api_key or settings.effective_tavily_api_key

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def search(
        self,
        query: str,
        max_results: int = 5,
        search_depth: str = "advanced",
        include_answer: bool = True,
        include_raw_content: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes an HTTP POST search against the official Tavily Search API.

        Never logs or exposes the API key.
        """
        key = self.api_key
        if not key:
            logger.error("[TruthLens] TAVILY_API_KEY is not configured")
            raise TavilyConfigError("Tavily API key is not configured")

        clean_query = query.strip()
        if not clean_query:
            return {"query": query, "answer": "", "results": []}

        payload = {
            "api_key": key,
            "query": clean_query,
            "search_depth": search_depth,
            "max_results": max(1, min(max_results, 10)),
            "include_answer": include_answer,
            "include_raw_content": include_raw_content,
        }

        logger.info(f"[TruthLens] Tavily search started for query: '{clean_query[:100]}'")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(TAVILY_API_URL, json=payload)

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", []) or []
                logger.info(f"[TruthLens] Tavily response received. Sources returned: {len(results)}")
                return {
                    "query": clean_query,
                    "answer": data.get("answer", "") or "",
                    "results": results,
                }
            elif response.status_code in (401, 403):
                logger.error("[TruthLens] Tavily authorization failed: invalid API key")
                raise TavilyConfigError("Tavily API key is not configured or invalid")
            elif response.status_code == 429:
                logger.warning("[TruthLens] Tavily rate limit exceeded")
                raise TavilyAPIError("Tavily rate limit exceeded. Please try again shortly.")
            else:
                logger.error(f"[TruthLens] Tavily API returned HTTP status {response.status_code}")
                raise TavilyAPIError("External source verification is temporarily unavailable")

        except httpx.TimeoutException:
            logger.error(f"[TruthLens] Tavily search timed out after {self.timeout}s")
            raise TavilyAPIError("External source verification is temporarily unavailable")
        except (TavilyConfigError, TavilyAPIError):
            raise
        except Exception as e:
            logger.error(f"[TruthLens] Unexpected error during Tavily search: {e}")
            raise TavilyAPIError("External source verification is temporarily unavailable")

    @staticmethod
    def extract_domain(url: Optional[str]) -> str:
        """Extract user-friendly domain name from URL."""
        if not url:
            return "Web Source"
        try:
            parsed = urlparse(url)
            netloc = parsed.netloc.lower()
            if netloc.startswith("www."):
                netloc = netloc[4:]
            return netloc or "Web Source"
        except Exception:
            return "Web Source"
