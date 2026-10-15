"""Unit tests for the EvidenceRetrievalEngine."""

import pytest
from app.services.retrieval.retriever import EvidenceRetrievalEngine


def test_evidence_search_google_founding():
    retriever = EvidenceRetrievalEngine()
    results = retriever.search_evidence("Google was founded by Larry Page and Sergey Brin", top_k=3)

    assert len(results) > 0
    top = results[0]
    assert "Google" in top.text or "Larry Page" in top.text
    assert top.relevance_score > 0.1
    assert top.authority_score > 0.8


def test_evidence_temporal_filtering():
    retriever = EvidenceRetrievalEngine()
    # Search with temporal year filter
    results = retriever.search_evidence("Apollo 11 Moon landing", top_k=3, temporal_filter_year=1969)
    assert len(results) > 0
    assert any("Apollo 11" in r.text or "1969" in r.text for r in results)
