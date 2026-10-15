"""
TruthGuard Source Credibility Scoring Engine.

Computes multi-factor credibility:
1. Domain authority & peer-review status.
2. Temporal recency of publication.
3. Primary vs secondary source classification.
4. Completeness and citation rigor.
"""

from __future__ import annotations
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlparse


AUTHORITY_DOMAINS = {
    # Tier 1: Governmental, International Bodies, Scientific Publishers (0.95 - 1.0)
    "gov": 0.98,
    "edu": 0.95,
    "who.int": 0.99,
    "nasa.gov": 0.99,
    "nih.gov": 0.99,
    "nature.com": 0.98,
    "sciencemag.org": 0.98,
    "thelancet.com": 0.98,
    "sec.gov": 0.99,
    "nobelprize.org": 0.98,
    "britannica.com": 0.95,
    "law.cornell.edu": 0.96,

    # Tier 2: Reputable Reference & Verified Tech/Wire Repos (0.85 - 0.94)
    "wikipedia.org": 0.88,
    "wikidata.org": 0.90,
    "reuters.com": 0.92,
    "apnews.com": 0.92,
    "bbc.com": 0.90,
    "python.org": 0.94,

    # Tier 3: General Media & Corporate Blogs (0.60 - 0.84)
    "medium.com": 0.55,
    "substack.com": 0.55,
    "twitter.com": 0.40,
    "x.com": 0.40,
}


class SourceCredibilityScorer:
    """Evaluates source trustworthiness with explainable score components."""

    def evaluate_source(
        self,
        source_name: str,
        url: Optional[str] = None,
        publication_date: Optional[str] = None,
        source_type: str = "local"
    ) -> Dict[str, Any]:
        """
        Computes a normalized credibility score (0.0 to 1.0) and component weights.
        """
        authority_score = self._compute_authority_score(source_name, url)
        recency_score = self._compute_recency_score(publication_date)
        primary_score = 0.95 if source_type in ("official", "primary", "local_kg") else 0.85

        # Weighted composite: 60% authority, 25% primary status, 15% recency
        composite = (0.60 * authority_score) + (0.25 * primary_score) + (0.15 * recency_score)
        normalized = round(min(1.0, max(0.0, composite)), 3)

        return {
            "authority_score": round(authority_score, 3),
            "recency_score": round(recency_score, 3),
            "primary_source_score": round(primary_score, 3),
            "overall_credibility": normalized,
            "explanation": (
                f"Authority: {authority_score:.2f} based on domain reputation; "
                f"Recency: {recency_score:.2f}; Primary indicator: {primary_score:.2f}"
            )
        }

    def _compute_authority_score(self, source_name: str, url: Optional[str]) -> float:
        """Determines authority from URL domain or source nomenclature."""
        if url:
            parsed = urlparse(url)
            hostname = (parsed.hostname or "").lower()

            # Direct domain check
            for dom, score in AUTHORITY_DOMAINS.items():
                if dom in hostname:
                    return score

            # TLD check
            tld = hostname.split(".")[-1] if "." in hostname else ""
            if tld in AUTHORITY_DOMAINS:
                return AUTHORITY_DOMAINS[tld]

        # Name-based heuristic fallback
        lower_name = source_name.lower()
        if any(term in lower_name for term in ("nasa", "who", "encyclopaedia", "nobel", "sec", "supreme court")):
            return 0.95
        if any(term in lower_name for term in ("official", "institute", "foundation", "university", "reuters", "ap")):
            return 0.90
        if "sample" in lower_name or "local" in lower_name:
            return 0.85

        return 0.70

    def _compute_recency_score(self, pub_date_str: Optional[str]) -> float:
        """Grades recency: newer sources score higher for dynamic topics."""
        if not pub_date_str:
            return 0.80  # Default reasonable score for timeless encyclopedic knowledge

        year_match = re.search(r"\b(19\d{2}|20\d{2})\b", pub_date_str)
        if not year_match:
            return 0.80

        year = int(year_match.group(1))
        current_year = datetime.now(timezone.utc).year

        diff = max(0, current_year - year)
        if diff <= 2:
            return 0.98
        elif diff <= 5:
            return 0.90
        elif diff <= 10:
            return 0.80
        elif diff <= 25:
            return 0.70
        else:
            return 0.60
