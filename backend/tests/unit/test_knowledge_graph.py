"""Unit tests for the KnowledgeGraphValidator."""

import pytest
from app.services.knowledge_graph.validator import KnowledgeGraphValidator


def test_kg_validation_einstein():
    kg = KnowledgeGraphValidator()
    res = kg.validate_claim(
        claim_text="Albert Einstein was born in Germany in 1879.",
        entities=["Albert Einstein", "Germany"]
    )
    assert res.entity_exists is True
    assert res.relationship_exists is True
    assert res.knowledge_graph_confidence >= 0.90
    assert len(res.matched_triples) > 0


def test_kg_temporal_conflict():
    kg = KnowledgeGraphValidator()
    # Claim says 1950, while facts.json says 1879
    res = kg.validate_claim(
        claim_text="Albert Einstein was born in Germany in 1950.",
        entities=["Albert Einstein", "Germany"]
    )
    assert res.entity_exists is True
    assert res.knowledge_graph_confidence < 0.50
