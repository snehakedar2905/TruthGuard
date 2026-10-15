"""
TruthGuard Verdict Aggregation Engine.

Aggregates multi-signal verification outputs into calibrated verdicts:
- Natural Language Inference (NLI)
- Evidence Retrieval Relevance
- Source Credibility & Authority
- Knowledge Graph Triples
- Cross-Model Consensus
- Temporal & Logical Consistency
- Source Context Faithfulness

Produces explainable verdict rationales and confidence scores.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.schemas.schemas import (
    ClaimVerdictResult,
    DomainType,
    EvidenceItem,
    ExtractedClaim,
    HallucinationType,
    VerdictType,
    VerificationSignals,
)


class VerdictAggregationEngine:
    """Combines orthogonal verification signals with domain-specific calibrations."""

    def __init__(self, app_settings: Optional[Any] = None) -> None:
        self.settings = app_settings or settings

    def aggregate_verdict(
        self,
        claim: ExtractedClaim,
        evidence: List[EvidenceItem],
        nli_entailment: float,
        nli_contradiction: float,
        kg_confidence: float,
        consensus_score: float,
        domain: DomainType = DomainType.GENERAL,
        input_context: Optional[str] = None
    ) -> ClaimVerdictResult:
        """
        Combines signals and applies domain threshold boundaries.
        """
        thresholds = self.settings.get_domain_thresholds(domain.value)
        sup_thresh = thresholds.get("support_threshold", 0.80)
        unc_thresh = thresholds.get("uncertainty_threshold", 0.60)
        con_thresh = thresholds.get("contradiction_threshold", 0.20)
        min_auth = thresholds.get("min_source_authority", 0.50)

        # 1. Compute retrieval and credibility weights
        if evidence:
            top_ev = evidence[0]
            retrieval_score = top_ev.relevance_score
            credibility_score = top_ev.authority_score
            temporal_validity = 1.0 if top_ev.temporal_validity else 0.20
        else:
            retrieval_score = 0.0
            credibility_score = 0.0
            temporal_validity = 0.50

        # 2. Check for Faithfulness against Input Context (if provided)
        context_inconsistent = False
        if input_context and input_context.strip():
            context_inconsistent = self._check_context_inconsistency(claim.text, input_context)

        # 3. Check for Internal Logical Contradiction Tag
        logically_inconsistent = (claim.type == HallucinationType.LOGICAL)

        # 4. Check for Explicit Temporal Contradiction
        temporally_inconsistent = False
        if claim.temporal_expressions:
            if nli_contradiction > 0.60:
                temporally_inconsistent = True
            elif evidence:
                all_ev_text = " ".join(e.text for e in evidence)
                ev_years = re.findall(r"\b(1[6-9]\d{2}|20\d{2})\b", all_ev_text)
                if ev_years and not set(claim.temporal_expressions).intersection(set(ev_years)):
                    temporally_inconsistent = True

        # 5. Composite Weighted Verification Score
        w = self.settings
        composite_score = (
            (w.weight_nli * nli_entailment) +
            (w.weight_retrieval * retrieval_score) +
            (w.weight_credibility * credibility_score) +
            (w.weight_knowledge_graph * kg_confidence) +
            (w.weight_consensus * consensus_score) +
            (w.weight_temporal * temporal_validity)
        )
        composite_score = round(min(1.0, max(0.0, composite_score)), 3)

        # 6. Apply Decision Tree for Verdict & Hallucination Type
        signals = VerificationSignals(
            nli=nli_entailment,
            retrieval=retrieval_score,
            knowledge_graph=kg_confidence,
            credibility=credibility_score,
            consensus=consensus_score,
            temporal=temporal_validity,
        )

        verdict: VerdictType
        hallucination_type: Optional[HallucinationType] = None
        explanation: str

        if context_inconsistent:
            verdict = VerdictType.CONTEXT_INCONSISTENT
            hallucination_type = HallucinationType.FAITHFUL
            confidence = 0.92
            explanation = (
                f"Claim contradicts the provided source context. "
                f"Source context does not support this assertion."
            )
        elif logically_inconsistent:
            verdict = VerdictType.LOGICALLY_INCONSISTENT
            hallucination_type = HallucinationType.LOGICAL
            confidence = 0.90
            explanation = "Claim contradicts another statement made in the same response."
        elif temporally_inconsistent:
            verdict = VerdictType.TEMPORALLY_INCONSISTENT
            hallucination_type = HallucinationType.TEMPORAL
            confidence = round(max(0.88, nli_contradiction), 2)
            explanation = (
                f"Dates or temporal ordering conflict with authoritative evidence "
                f"(Claim year: {claim.temporal_expressions} vs Evidence: {evidence[0].text[:80]}...)."
            )
        elif nli_contradiction >= con_thresh and nli_contradiction > nli_entailment:
            verdict = VerdictType.CONTRADICTED
            hallucination_type = HallucinationType.FACTUAL
            confidence = round(nli_contradiction, 2)
            explanation = (
                f"Authoritative evidence directly contradicts this claim. "
                f"Contradiction score: {nli_contradiction:.2f}; "
                f"Evidence: \"{evidence[0].text if evidence else 'N/A'}\""
            )
        elif composite_score >= sup_thresh and credibility_score >= min_auth:
            if claim.type == HallucinationType.ENTITY and kg_confidence <= 0.20 and retrieval_score < 0.60:
                verdict = VerdictType.ENTITY_UNSUPPORTED
                hallucination_type = HallucinationType.ENTITY
                confidence = 0.65
                explanation = f"Entities {claim.entities} could not be confirmed in authoritative knowledge graph or external web evidence."
            else:
                verdict = VerdictType.SUPPORTED
                hallucination_type = HallucinationType.NONE
                confidence = composite_score
                explanation = (
                    f"Claim is supported by high-credibility evidence. "
                    f"NLI Entailment: {nli_entailment:.2f}; KG Match: {kg_confidence:.2f}; "
                    f"Source Authority: {credibility_score:.2f}."
                )
        elif composite_score >= unc_thresh:
            verdict = VerdictType.PARTIALLY_SUPPORTED
            hallucination_type = None
            confidence = composite_score
            explanation = (
                f"Evidence partially aligns with claim, but confidence ({composite_score:.2f}) "
                f"is below domain support threshold ({sup_thresh:.2f})."
            )
        elif not evidence or retrieval_score < 0.25:
            verdict = VerdictType.UNVERIFIABLE
            hallucination_type = HallucinationType.FACTUAL
            confidence = 0.50
            explanation = "Insufficient authoritative evidence found to verify or refute this claim."
        else:
            verdict = VerdictType.ENTITY_UNSUPPORTED if claim.entities else VerdictType.UNVERIFIABLE
            hallucination_type = HallucinationType.ENTITY if claim.entities else HallucinationType.FACTUAL
            confidence = 0.60
            explanation = "Entities or relationships could not be confirmed by credible sources."

        return ClaimVerdictResult(
            claim_id=claim.claim_id,
            claim_text=claim.text,
            verdict=verdict,
            confidence=confidence,
            hallucination_type=hallucination_type,
            signals=signals,
            evidence=evidence,
            explanation=explanation,
        )

    def _check_context_inconsistency(self, claim_text: str, context: str) -> bool:
        """Determines if a claim directly contradicts factual assertions in source context."""
        c_years = re.findall(r"\b(1[6-9]\d{2}|20\d{2})\b", claim_text)
        ctx_years = re.findall(r"\b(1[6-9]\d{2}|20\d{2})\b", context)

        # Context specifies year X, claim asserts year Y for overlapping topics
        if c_years and ctx_years:
            if not set(c_years).intersection(set(ctx_years)):
                c_words = set(re.findall(r"\w+", claim_text.lower()))
                ctx_words = set(re.findall(r"\w+", context.lower()))
                if len(c_words.intersection(ctx_words)) >= 2:
                    return True

        return False
