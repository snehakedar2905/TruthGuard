"""Unit tests for the SourceCredibilityScorer."""

import pytest
from app.services.credibility.scorer import SourceCredibilityScorer


def test_credibility_tier1_domain():
    scorer = SourceCredibilityScorer()
    res = scorer.evaluate_source(
        source_name="WHO",
        url="https://www.who.int/health-topics/coronavirus",
        publication_date="2024-01-01",
        source_type="primary"
    )
    assert res["overall_credibility"] >= 0.90
    assert res["authority_score"] >= 0.95


def test_credibility_open_web():
    scorer = SourceCredibilityScorer()
    res = scorer.evaluate_source(
        source_name="Random Blog",
        url="https://medium.com/@user/story",
        publication_date="2020-01-01"
    )
    assert res["overall_credibility"] < 0.75
