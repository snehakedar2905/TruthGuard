"""Unit tests for the CorrectionEngine."""

import pytest
from app.schemas.schemas import (
    ClaimVerdictResult,
    DomainType,
    EvidenceItem,
    HallucinationType,
    VerdictType,
    VerificationSignals,
)
from app.services.correction.engine import CorrectionEngine


def test_correction_rewrites_contradicted_claim():
    engine = CorrectionEngine()
    original_text = "Google was founded in 1999."
    verdicts = [
        ClaimVerdictResult(
            claim_id="c_1",
            claim_text="Google was founded in 1999.",
            verdict=VerdictType.CONTRADICTED,
            confidence=0.94,
            hallucination_type=HallucinationType.FACTUAL,
            signals=VerificationSignals(),
            evidence=[
                EvidenceItem(
                    evidence_id="e_1",
                    source="Alphabet",
                    text="Google was founded on September 4, 1998, by Larry Page and Sergey Brin.",
                    relevance_score=0.95,
                    authority_score=0.98
                )
            ],
            explanation="Contradicted by SEC filing."
        )
    ]

    res = engine.correct_response(original_text, verdicts)
    assert "1998" in res.corrected_output
    assert res.corrected_claims_count == 1


def test_correction_preserves_supported_claim():
    engine = CorrectionEngine()
    original_text = "The Earth revolves around the Sun."
    verdicts = [
        ClaimVerdictResult(
            claim_id="c_2",
            claim_text="The Earth revolves around the Sun.",
            verdict=VerdictType.SUPPORTED,
            confidence=0.98,
            hallucination_type=None,
            signals=VerificationSignals(),
            evidence=[],
            explanation="Verified fact."
        )
    ]

    res = engine.correct_response(original_text, verdicts)
    assert res.corrected_output == original_text
    assert res.preserved_claims_count == 1
