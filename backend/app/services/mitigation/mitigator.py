"""
TruthGuard Hallucination Mitigation Module.

Provides prompt augmentation and evidence grounding strategies prior to generation:
1. Retrieval-Augmented Grounding (RAG) prompt composition.
2. Evidence-aware strict boundary system prompts.
3. Citation & uncertainty formatting constraints.
"""

from __future__ import annotations
from typing import List, Optional
from app.schemas.schemas import EvidenceItem


EVIDENCE_AWARE_SYSTEM_PROMPT = """You are a strictly grounded, factual assistant.
Rules:
1. Answer the query ONLY using the provided verified evidence.
2. If the verified evidence is insufficient or does not explicitly contain the answer, state: "The requested information cannot be verified from available authoritative sources."
3. Do NOT invent dates, names, organizations, or numbers.
4. Cite the source title or URL after each factual assertion."""


class MitigationService:
    """Pre-generation mitigation and prompt grounding utility."""

    def build_grounded_prompt(
        self,
        user_query: str,
        retrieved_evidence: List[EvidenceItem],
        domain: str = "general"
    ) -> str:
        """Constructs an evidence-grounded prompt to prevent hallucinations."""
        evidence_block = "\n".join(
            f"[{idx+1}] Source: {ev.source} (Authority: {ev.authority_score:.2f})\nText: {ev.text}"
            for idx, ev in enumerate(retrieved_evidence)
        )

        return (
            f"{EVIDENCE_AWARE_SYSTEM_PROMPT}\n\n"
            f"--- VERIFIED EVIDENCE ---\n"
            f"{evidence_block if evidence_block else 'No external evidence available.'}\n\n"
            f"--- USER QUERY ---\n"
            f"{user_query}\n\n"
            f"--- GROUNDED RESPONSE ---"
        )
