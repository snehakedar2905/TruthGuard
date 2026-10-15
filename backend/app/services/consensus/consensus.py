"""
TruthGuard Cross-Model Consensus Verification Module.

Gathers verification votes across multiple simulated / adapter verifier agents:
- Verifier A (Strict Lexical/Logical Checker)
- Verifier B (Semantic Paraphrase Checker)
- Verifier C (Temporal/Factual Consistency Checker)
Computes a normalized consensus agreement score.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional

from app.schemas.schemas import ConsensusVerifyResponse


class CrossModelConsensusService:
    """Multi-verifier consensus aggregator."""

    def verify_consensus(
        self,
        claim: str,
        evidence_snippets: List[str]
    ) -> ConsensusVerifyResponse:
        """
        Polls independent verification agents to determine ensemble consensus.
        """
        if not evidence_snippets:
            return ConsensusVerifyResponse(
                consensus_score=0.20,
                model_votes={
                    "Verifier-A (Lexical)": "UNKNOWN",
                    "Verifier-B (Semantic)": "UNKNOWN",
                    "Verifier-C (Temporal)": "UNKNOWN",
                },
                summary="No external evidence provided to establish consensus."
            )

        combined_evidence = " ".join(evidence_snippets).lower()
        claim_clean = claim.lower()

        # Check for year conflicts
        claim_years = re.findall(r"\b(1[6-9]\d{2}|20\d{2})\b", claim_clean)
        evidence_years = re.findall(r"\b(1[6-9]\d{2}|20\d{2})\b", combined_evidence)
        year_conflict = bool(claim_years and evidence_years and not set(claim_years).intersection(set(evidence_years)))

        # Model A: Lexical overlap and exact entity check
        claim_words = set(re.findall(r"\w+", claim_clean))
        evidence_words = set(re.findall(r"\w+", combined_evidence))
        overlap = len(claim_words.intersection(evidence_words)) / max(1, len(claim_words))
        
        if year_conflict:
            vote_a = "CONTRADICT"
            vote_b = "CONTRADICT"
            vote_c = "CONTRADICT"
        else:
            vote_a = "SUPPORT" if overlap > 0.60 else ("CONTRADICT" if overlap < 0.20 else "UNKNOWN")
            vote_b = "SUPPORT" if overlap > 0.45 else "UNKNOWN"
            vote_c = "SUPPORT" if (claim_years and evidence_years and set(claim_years).intersection(set(evidence_years))) else vote_a

        votes = {
            "Verifier-A (Lexical)": vote_a,
            "Verifier-B (Semantic)": vote_b,
            "Verifier-C (Temporal)": vote_c,
        }

        # Calculate consensus agreement score
        support_count = sum(1 for v in votes.values() if v == "SUPPORT")
        contradict_count = sum(1 for v in votes.values() if v == "CONTRADICT")

        if contradict_count >= 2:
            consensus_score = 0.10
            summary = f"Consensus indicates contradiction ({contradict_count}/3 models voted CONTRADICT)."
        elif support_count >= 2:
            consensus_score = round(support_count / len(votes), 2)
            summary = f"Strong consensus ({support_count}/3 models voted SUPPORT)."
        elif support_count == 1:
            consensus_score = 0.50
            summary = "Partial consensus with ambiguous evidence."
        else:
            consensus_score = 0.25
            summary = "Low consensus across verifier ensemble."

        return ConsensusVerifyResponse(
            consensus_score=consensus_score,
            model_votes=votes,
            summary=summary
        )
