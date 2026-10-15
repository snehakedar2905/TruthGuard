"""
TruthGuard Knowledge Graph Validation Engine.

Validates claims against structured triples <Subject, Predicate, Object>.
Checks:
- Entity existence in knowledge graph
- Predicate / relation existence
- Attribute and value consistency
- Temporal consistency (e.g. matching timestamps/years)
"""

from __future__ import annotations
import json
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.schemas.schemas import KGVerifyResponse


class KnowledgeGraphValidator:
    """Validates factual propositions against knowledge graph triples."""

    def __init__(self, kg_path: Optional[str] = None) -> None:
        self.triples: List[Dict[str, Any]] = []
        self._load_triples(kg_path)

    def _load_triples(self, path: Optional[str]) -> None:
        """Load knowledge graph triples from JSON."""
        default_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "..", "data", "knowledge_graph", "facts.json"
        )
        target = path or os.path.abspath(default_path)

        if os.path.exists(target):
            with open(target, "r", encoding="utf-8") as f:
                self.triples = json.load(f)
        else:
            self.triples = []

    def validate_claim(
        self,
        claim_text: str,
        entities: Optional[List[str]] = None
    ) -> KGVerifyResponse:
        """
        Extracts candidate triples and compares against the graph store.
        """
        claim_lower = claim_text.lower()
        extracted_entities = entities or []
        matched_triples: List[Dict[str, Any]] = []

        entity_found = False
        relation_found = False
        temporal_conflict = False

        claim_years = re.findall(r"\b(1[6-9]\d{2}|20\d{2})\b", claim_text)

        for triple in self.triples:
            subj = triple.get("subject", "").lower()
            obj = triple.get("object", "").lower()
            pred = triple.get("predicate", "").lower()
            t_year = triple.get("temporal_year")

            # Check if subject or object is mentioned
            subj_match = subj in claim_lower or any(subj in e.lower() for e in extracted_entities)
            obj_match = obj in claim_lower or any(obj in e.lower() for e in extracted_entities)

            if subj_match:
                entity_found = True

            if subj_match and (obj_match or self._predicate_matches(pred, claim_lower)):
                relation_found = True
                matched_triples.append(triple)

                # Check temporal consistency
                if t_year and claim_years:
                    if str(t_year) not in claim_years:
                        temporal_conflict = True

        # Calculate graph confidence
        if entity_found and relation_found and not temporal_conflict:
            confidence = 0.95
        elif entity_found and relation_found and temporal_conflict:
            confidence = 0.15  # Contradicts graph temporal attribute
        elif entity_found:
            confidence = 0.50
        else:
            confidence = 0.20

        return KGVerifyResponse(
            entity_exists=entity_found,
            relationship_exists=relation_found,
            knowledge_graph_confidence=confidence,
            matched_triples=matched_triples
        )

    def _predicate_matches(self, predicate: str, text: str) -> bool:
        """Check if predicate concept appears in text."""
        pred_tokens = predicate.replace("_", " ").split()
        return all(tok in text for tok in pred_tokens)
