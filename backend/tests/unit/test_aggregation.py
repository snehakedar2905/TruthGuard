"""Unit tests for the VerdictAggregationEngine."""

import pytest
from app.schemas.schemas import DomainType, EvidenceItem, ExtractedClaim, HallucinationType, VerdictType
from app.services.aggregation.aggregator import VerdictAggregationEngine


def test_aggregate_supported_verdict():
    aggregator = VerdictAggregationEngine()
    claim = ExtractedClaim(
        claim_id="c_1",
        text="The Earth revolves around the Sun.",
        type=HallucinationType.FACTUAL
    )
    evidence = [
        EvidenceItem(
            evidence_id="e_1",
            source="NASA",
            url="https://nasa.gov",
            title="Solar System",
            text="The Earth revolves around the Sun in an elliptical orbit.",
            relevance_score=0.98,
            authority_score=0.99
        )
    ]

    res = aggregator.aggregate_verdict(
        claim=claim,
        evidence=evidence,
        nli_entailment=0.95,
        nli_contradiction=0.01,
        kg_confidence=0.99,
        consensus_score=1.0,
        domain=DomainType.GENERAL
    )

    assert res.verdict == VerdictType.SUPPORTED
    assert res.confidence >= 0.85


def test_aggregate_contradicted_verdict():
    aggregator = VerdictAggregationEngine()
    claim = ExtractedClaim(
        claim_id="c_2",
        text="Google was founded in 1999.",
        type=HallucinationType.TEMPORAL,
        temporal_expressions=["1999"]
    )
    evidence = [
        EvidenceItem(
            evidence_id="e_2",
            source="Alphabet SEC",
            url="https://sec.gov",
            title="Corporate History",
            text="Google was founded in 1998 by Larry Page and Sergey Brin.",
            relevance_score=0.90,
            authority_score=0.98
        )
    ]

    res = aggregator.aggregate_verdict(
        claim=claim,
        evidence=evidence,
        nli_entailment=0.05,
        nli_contradiction=0.92,
        kg_confidence=0.15,
        consensus_score=0.10,
        domain=DomainType.GENERAL
    )

    assert res.verdict in (VerdictType.CONTRADICTED, VerdictType.TEMPORALLY_INCONSISTENT)
    assert res.hallucination_type in (HallucinationType.FACTUAL, HallucinationType.TEMPORAL)
