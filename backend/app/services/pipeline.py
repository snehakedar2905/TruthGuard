"""
TruthGuard Master Orchestration Pipeline.

Coordinates:
1. Extraction & Decomposition
2. Hybrid Multi-Hop Retrieval
3. Concurrent Multi-Signal Verification (NLI, KG, Consensus, Credibility)
4. Domain-Gated Verdict Aggregation
5. Constrained Correction & Report Synthesis
"""

from __future__ import annotations
import asyncio
from datetime import datetime, timezone
import time
import uuid
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.logging import ModuleTimer, logger
from app.models.database import (
    AnalysisRecord,
    ClaimRecord,
    CorrectionRecord,
    EvidenceRecord,
    SessionLocal,
    VerificationRecord,
)
from app.schemas.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    ClaimVerdictResult,
    DomainType,
    EvidenceItem,
    ExtractedClaim,
)
from app.services.aggregation.aggregator import VerdictAggregationEngine
from app.services.claim_extractor.extractor import ClaimExtractorService
from app.services.consensus.consensus import CrossModelConsensusService
from app.services.correction.engine import CorrectionEngine
from app.services.knowledge_graph.validator import KnowledgeGraphValidator
from app.services.nli.verifier import NLIVerificationService
from app.services.retrieval.retriever import EvidenceRetrievalEngine


class TruthGuardPipeline:
    """End-to-end asynchronous verification and correction pipeline."""

    def __init__(self) -> None:
        self.extractor = ClaimExtractorService()
        self.retriever = EvidenceRetrievalEngine()
        self.nli_service = NLIVerificationService()
        self.kg_validator = KnowledgeGraphValidator()
        self.consensus_service = CrossModelConsensusService()
        self.aggregator = VerdictAggregationEngine()
        self.correction_engine = CorrectionEngine()

    async def run_pipeline(self, request: AnalyzeRequest) -> AnalyzeResponse:
        """Executes the full verification and correction workflow with latency tracing."""
        analysis_id = f"analysis_{uuid.uuid4().hex[:8]}"
        start_time = time.perf_counter()

        logger.info(f"Starting TruthGuard analysis id={analysis_id} domain={request.domain.value}")

        # 1. Claim Extraction
        with ModuleTimer("claim_extraction", analysis_id):
            claims = self.extractor.extract_claims(
                text=request.llm_output,
                context=request.input_context
            )

        if not claims:
            # Empty or conversational input with no substantive claims
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return AnalyzeResponse(
                analysis_id=analysis_id,
                original_output=request.llm_output,
                overall_score=1.0,
                domain=request.domain.value,
                claims=[],
                verdicts=[],
                corrected_output=request.llm_output,
                corrections=[],
                evidence=[],
                processing_time_ms=round(elapsed_ms, 2),
                is_mock=settings.mock_mode
            )

        # 2. Parallel Multi-Signal Verification across all claims
        with ModuleTimer("multi_signal_verification", analysis_id):
            verification_tasks = [
                self._verify_single_claim(claim, request.domain, request.input_context)
                for claim in claims
            ]
            claim_verdicts: List[ClaimVerdictResult] = await asyncio.gather(*verification_tasks)

        # 3. Evidence Aggregation & Score Calculation
        all_evidence: List[EvidenceItem] = []
        for v in claim_verdicts:
            for ev in v.evidence:
                if not any(e.evidence_id == ev.evidence_id for e in all_evidence):
                    all_evidence.append(ev)

        overall_score = round(
            sum(v.confidence for v in claim_verdicts) / max(1, len(claim_verdicts)),
            3
        )

        # 4. Evidence-Grounded Correction
        with ModuleTimer("correction_generation", analysis_id):
            if request.apply_correction:
                corr_res = self.correction_engine.correct_response(
                    original_output=request.llm_output,
                    verdicts=claim_verdicts,
                    domain=request.domain
                )
                corrected_output = corr_res.corrected_output
                corrections = corr_res.corrections
            else:
                corrected_output = request.llm_output
                corrections = []

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        # 5. Persist to Database if retention enabled or SQLite configured
        self._persist_session(
            analysis_id=analysis_id,
            request=request,
            corrected_output=corrected_output,
            overall_score=overall_score,
            elapsed_ms=elapsed_ms,
            claims=claims,
            verdicts=claim_verdicts,
            corrections=corrections
        )

        return AnalyzeResponse(
            analysis_id=analysis_id,
            original_output=request.llm_output,
            overall_score=overall_score,
            domain=request.domain.value,
            claims=claims,
            verdicts=claim_verdicts,
            corrected_output=corrected_output,
            corrections=corrections,
            evidence=all_evidence,
            processing_time_ms=round(elapsed_ms, 2),
            is_mock=settings.mock_mode
        )

    async def _verify_single_claim(
        self,
        claim: ExtractedClaim,
        domain: DomainType,
        input_context: Optional[str]
    ) -> ClaimVerdictResult:
        """Asynchronously runs retrieval, NLI, KG, and Consensus for one claim."""
        logger.info("[TruthLens] Claim verification started")
        logger.info(f"[TruthLens] Claim: {claim.text}")

        # 1. Retrieve real external evidence via Tavily
        query = self.retriever.generate_search_query(claim)
        evidence = await self.retriever.search_evidence_async(
            query=query,
            claim_id=claim.claim_id,
            top_k=5,
            use_tavily=True
        )

        ev_text = "\n".join(e.text for e in evidence[:3]) if evidence else ""
        ev_snippets = [e.text for e in evidence]

        # 2. Concurrently evaluate NLI, KG, and Consensus
        async def run_nli():
            return self.nli_service.verify_pair(claim=claim.text, evidence=ev_text)

        async def run_kg():
            return self.kg_validator.validate_claim(claim_text=claim.text, entities=claim.entities)

        async def run_consensus():
            return self.consensus_service.verify_consensus(claim=claim.text, evidence_snippets=ev_snippets)

        nli_res, kg_res, consensus_res = await asyncio.gather(
            run_nli(),
            run_kg(),
            run_consensus()
        )
        logger.info(f"[TruthLens] NLI output for '{claim.text}': {nli_res}")

        # 3. Aggregate Verdict
        verdict = self.aggregator.aggregate_verdict(
            claim=claim,
            evidence=evidence,
            nli_entailment=nli_res.entailment,
            nli_contradiction=nli_res.contradiction,
            kg_confidence=kg_res.knowledge_graph_confidence,
            consensus_score=consensus_res.consensus_score,
            domain=domain,
            input_context=input_context
        )

        logger.info(f"[TruthLens] Claim verification completed: {verdict.verdict.value} (confidence={verdict.confidence})")
        return verdict

    def _persist_session(
        self,
        analysis_id: str,
        request: AnalyzeRequest,
        corrected_output: str,
        overall_score: float,
        elapsed_ms: float,
        claims: List[ExtractedClaim],
        verdicts: List[ClaimVerdictResult],
        corrections: List[Any]
    ) -> None:
        """Saves analysis run and retrieved Tavily evidence into SQLAlchemy database."""
        try:
            db = SessionLocal()
            analysis_rec = AnalysisRecord(
                id=analysis_id,
                input_context=request.input_context,
                original_output=request.llm_output,
                corrected_output=corrected_output,
                domain=request.domain.value,
                language=request.language,
                overall_confidence=overall_score,
                processing_time_ms=elapsed_ms
            )
            db.add(analysis_rec)

            for idx, c in enumerate(claims):
                c_rec = ClaimRecord(
                    id=f"{analysis_id}_{c.claim_id}",
                    analysis_id=analysis_id,
                    claim_text=c.text,
                    claim_type=c.type.value,
                    entities=c.entities,
                    temporal_expressions=c.temporal_expressions,
                    claim_order=idx
                )
                db.add(c_rec)

                # Attach verification record and evidence items if available
                v_res = next((v for v in verdicts if v.claim_id == c.claim_id), None)
                if v_res:
                    v_rec = VerificationRecord(
                        claim_id=c_rec.id,
                        nli_score=v_res.signals.nli,
                        retrieval_score=v_res.signals.retrieval,
                        kg_score=v_res.signals.knowledge_graph,
                        consensus_score=v_res.signals.consensus,
                        credibility_score=v_res.signals.credibility,
                        temporal_score=v_res.signals.temporal,
                        final_score=v_res.confidence,
                        verdict=v_res.verdict.value,
                        explanation=v_res.explanation
                    )
                    db.add(v_rec)

                    for ev in v_res.evidence:
                        ev_rec = EvidenceRecord(
                            id=f"ev_{uuid.uuid4().hex[:12]}",
                            claim_id=c_rec.id,
                            source=ev.source,
                            url=ev.url,
                            title=ev.title,
                            content=ev.text,
                            relevance_score=ev.relevance_score,
                            authority_score=ev.authority_score,
                            publication_date=ev.publication_date,
                            retrieved_at=datetime.now(timezone.utc)
                        )
                        db.add(ev_rec)

            db.commit()
            db.close()
        except Exception as e:
            logger.warning(f"Could not persist analysis session to DB: {e}")
