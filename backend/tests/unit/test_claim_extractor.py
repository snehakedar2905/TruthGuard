"""Unit tests for the ClaimExtractorService."""

import pytest
from app.services.claim_extractor.extractor import ClaimExtractorService
from app.schemas.schemas import HallucinationType


def test_atomic_claim_decomposition():
    extractor = ClaimExtractorService()
    text = "Albert Einstein was born in Germany in 1879 and developed the theory of relativity."
    claims = extractor.extract_claims(text)

    assert len(claims) >= 2
    claim_texts = [c.text for c in claims]
    assert any("1879" in t for t in claim_texts)
    assert any("theory of relativity" in t.lower() for t in claim_texts)

    # Check entity extraction
    all_entities = [e for c in claims for e in c.entities]
    assert any("Einstein" in e for e in all_entities)

    # Check temporal extraction
    all_temporals = [t for c in claims for t in c.temporal_expressions]
    assert "1879" in all_temporals


def test_sentence_segmentation_with_abbreviations():
    extractor = ClaimExtractorService()
    text = "Dr. Smith announced a discovery. The event occurred in 2024."
    claims = extractor.extract_claims(text)

    # Must not break on "Dr."
    assert len(claims) == 2
    assert claims[0].text.startswith("Dr. Smith")


def test_filter_conversational_pleasantries():
    extractor = ClaimExtractorService()
    text = "Hello! I would be glad to help you today. The Earth revolves around the Sun."
    claims = extractor.extract_claims(text)

    assert len(claims) == 1
    assert "Earth revolves around the Sun" in claims[0].text


def test_logical_contradiction_detection():
    extractor = ClaimExtractorService()
    text = "The company was founded in 2010. The company was founded in 2015."
    claims = extractor.extract_claims(text)

    assert len(claims) == 2
    assert all(c.type == HallucinationType.LOGICAL for c in claims)
