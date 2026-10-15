"""Unit tests for the CrossModelConsensusService."""

import pytest
from app.services.consensus.consensus import CrossModelConsensusService


def test_consensus_agreement():
    service = CrossModelConsensusService()
    claim = "The Earth revolves around the Sun."
    evidence = ["The Earth revolves around the Sun in an elliptical orbit."]
    res = service.verify_consensus(claim, evidence)

    assert res.consensus_score >= 0.60
    assert len(res.model_votes) == 3


def test_consensus_contradiction():
    service = CrossModelConsensusService()
    claim = "Google was founded in 1999."
    evidence = ["Google was founded on September 4, 1998."]
    res = service.verify_consensus(claim, evidence)

    assert res.consensus_score <= 0.35
