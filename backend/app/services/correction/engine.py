"""
TruthGuard Evidence-Based Correction Engine.

Rewrites unsupported or contradicted claims using retrieved evidence:
1. Replaces contradicted facts (dates, entities, events) with exact evidence-grounded statements.
2. Hedging/flagging for UNVERIFIABLE or ENTITY_UNSUPPORTED statements.
3. Resolves internal logical contradictions.
4. Preserves semantic coherence and verified claims intact.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Tuple

from app.schemas.schemas import (
    ClaimVerdictResult,
    CorrectionItem,
    CorrectionResponse,
    DomainType,
    VerdictType,
)


class CorrectionEngine:
    """Constrained, minimally invasive factual correction service."""

    def correct_response(
        self,
        original_output: str,
        verdicts: List[ClaimVerdictResult],
        domain: DomainType = DomainType.GENERAL
    ) -> CorrectionResponse:
        """
        Synthesizes an evidence-grounded corrected response from claim evaluations.
        """
        corrected_text = original_output
        corrections: List[CorrectionItem] = []

        preserved_count = 0
        corrected_count = 0
        unverifiable_count = 0

        for res in verdicts:
            c_text = res.claim_text.strip()
            # If claim ends with a period, ensure search pattern can match it
            c_pattern = re.escape(c_text.rstrip("."))

            if res.verdict == VerdictType.SUPPORTED:
                preserved_count += 1
                corrections.append(
                    CorrectionItem(
                        claim_id=res.claim_id,
                        original_claim=c_text,
                        corrected_claim=c_text,
                        reason="Claim is supported by external evidence; preserved.",
                        evidence_ids=[e.evidence_id for e in res.evidence],
                        action="preserved"
                    )
                )

            elif res.verdict in (
                VerdictType.CONTRADICTED,
                VerdictType.TEMPORALLY_INCONSISTENT,
                VerdictType.CONTEXT_INCONSISTENT,
                VerdictType.LOGICALLY_INCONSISTENT
            ):
                corrected_count += 1
                # Generate replacement fact from top evidence
                replacement = self._generate_evidence_replacement(res)
                corrected_text = self._replace_claim_span(corrected_text, c_text, replacement)

                corrections.append(
                    CorrectionItem(
                        claim_id=res.claim_id,
                        original_claim=c_text,
                        corrected_claim=replacement,
                        reason=f"Corrected based on {res.verdict.value.lower().replace('_', ' ')}: {res.explanation}",
                        evidence_ids=[e.evidence_id for e in res.evidence],
                        action="corrected"
                    )
                )

            elif res.verdict in (VerdictType.UNVERIFIABLE, VerdictType.ENTITY_UNSUPPORTED):
                unverifiable_count += 1
                hedged_replacement = f"[Unverified: {c_text}]"
                corrected_text = self._replace_claim_span(corrected_text, c_text, hedged_replacement)

                corrections.append(
                    CorrectionItem(
                        claim_id=res.claim_id,
                        original_claim=c_text,
                        corrected_claim=hedged_replacement,
                        reason="Insufficient authoritative evidence found to verify; flagged as unverified.",
                        evidence_ids=[],
                        action="flagged_unverifiable"
                    )
                )

        return CorrectionResponse(
            original_output=original_output,
            corrected_output=corrected_text.strip(),
            corrections=corrections,
            preserved_claims_count=preserved_count,
            corrected_claims_count=corrected_count,
            unverifiable_claims_count=unverifiable_count
        )

    def _generate_evidence_replacement(self, verdict_result: ClaimVerdictResult) -> str:
        """Derives minimal replacement proposition directly from evidence."""
        if not verdict_result.evidence:
            return f"[Unverified claim removed: {verdict_result.claim_text}]"

        ev_sentences = []
        for ev in verdict_result.evidence:
            for s in re.split(r"[.!?\n]+", ev.text):
                clean_s = s.strip()
                if len(clean_s) > 10:
                    ev_sentences.append(clean_s)

        if not ev_sentences:
            return f"[Unverified claim removed: {verdict_result.claim_text}]"

        claim_words = set(re.findall(r"\w+", verdict_result.claim_text.lower()))
        best_sentence = ev_sentences[0]
        best_overlap = 0

        for sent in ev_sentences:
            s_words = set(re.findall(r"\w+", sent.lower()))
            overlap = len(claim_words.intersection(s_words))
            if overlap > best_overlap:
                best_overlap = overlap
                best_sentence = sent

        if not best_sentence.endswith("."):
            best_sentence += "."

        return best_sentence

    def _replace_claim_span(self, full_text: str, original_claim: str, replacement: str) -> str:
        """Substitutes claim in text while avoiding destroying formatting."""
        # Try direct literal replacement
        clean_orig = original_claim.strip()
        if clean_orig in full_text:
            return full_text.replace(clean_orig, replacement, 1)

        # Try stripped punctuation
        stripped = clean_orig.rstrip(".!?")
        if stripped in full_text:
            return full_text.replace(stripped, replacement.rstrip(".!?"), 1)

        # Fallback to appending replacement
        return f"{full_text}\n[Correction note: {replacement}]"
