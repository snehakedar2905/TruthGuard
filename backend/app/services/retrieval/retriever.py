"""
TruthGuard Hybrid Evidence Retrieval System.

Supports:
1. Dense vector semantic retrieval (Cosine similarity with embeddings / TF-IDF fallback).
2. Sparse keyword BM25-style term-frequency matching.
3. Hybrid rank fusion.
4. Multi-hop entity graph traversal to gather contextually linked passages.
5. Temporal filtering and deduplication.
"""

from __future__ import annotations
import json
import math
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import hashlib
import logging
from app.core.config import settings
from app.schemas.schemas import EvidenceItem
from app.services.credibility.scorer import SourceCredibilityScorer
from app.services.retrieval.tavily_client import (
    TavilySearchClient,
    TavilyConfigError,
    TavilyAPIError,
)

logger = logging.getLogger("truthlens.retrieval")


class EvidenceRetrievalEngine:
    """Hybrid multi-hop evidence retrieval and ranking engine with live Tavily Web Search."""

    def __init__(
        self,
        data_path: Optional[str] = None,
        tavily_client: Optional[TavilySearchClient] = None
    ) -> None:
        self.credibility_scorer = SourceCredibilityScorer()
        self.tavily_client = tavily_client or TavilySearchClient()
        self.documents: List[Dict[str, Any]] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self._load_knowledge_base(data_path)

    def _load_knowledge_base(self, path: Optional[str]) -> None:
        """Load standard knowledge corpus."""
        default_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "..", "data", "datasets", "knowledge_store.json"
        )
        target_path = path or os.path.abspath(default_path)

        if os.path.exists(target_path):
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    self.documents = json.load(f)
            except Exception:
                self.documents = []
        else:
            self.documents = [
                {
                    "id": "kb_default_01",
                    "title": "Google Founding",
                    "source": "Corporate Records",
                    "url": "https://about.google",
                    "text": "Google was founded in 1998 by Larry Page and Sergey Brin.",
                    "authority_score": 0.95,
                    "publication_date": "2024-01-01",
                    "entities": ["Google", "Larry Page", "Sergey Brin"]
                },
                {
                    "id": "kb_default_02",
                    "title": "Earth Orbit",
                    "source": "NASA Science",
                    "url": "https://science.nasa.gov",
                    "text": "The Earth revolves around the Sun in an elliptical orbit.",
                    "authority_score": 0.99,
                    "publication_date": "2024-01-01",
                    "entities": ["Earth", "Sun"]
                }
            ]

        self._build_sparse_index()

    def _build_sparse_index(self) -> None:
        """Construct TF-IDF vector space for dense/sparse semantic queries."""
        if not self.documents:
            return
        corpus = [doc.get("text", "") + " " + doc.get("title", "") for doc in self.documents]
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)

    def generate_search_query(self, claim_input: Any) -> str:
        """
        Derives an optimized search query from an atomic claim or string.
        Strips quotes, trailing punctuation, and redundant filler while retaining key entities, dates, and predicates.
        """
        if hasattr(claim_input, "text"):
            raw_text = claim_input.text
        else:
            raw_text = str(claim_input)

        query = re.sub(r'["\']', '', raw_text).strip()
        query = re.sub(r'\s*\.\s*$', '', query).strip()
        query = re.sub(r'^(it is known that|studies show that|research indicates that|claim:\s*)', '', query, flags=re.IGNORECASE).strip()
        return query or raw_text

    async def search_evidence_async(
        self,
        query: str,
        claim_id: Optional[str] = None,
        top_k: int = 5,
        min_similarity: float = 0.20,
        temporal_filter_year: Optional[int] = None,
        use_tavily: bool = True
    ) -> List[EvidenceItem]:
        """
        Retrieves real external web evidence via Tavily API in production flow.
        Falls back to local corpus ONLY if mock_mode is explicitly enabled.
        """
        clean_query = self.generate_search_query(query)
        if not clean_query:
            return []

        if use_tavily:
            if not self.tavily_client.is_configured():
                if settings.mock_mode:
                    logger.warning("[TruthLens] TAVILY_API_KEY is not configured and mock_mode is True; falling back to local corpus")
                    return self._search_local_kb(clean_query, claim_id, top_k, min_similarity, temporal_filter_year)
                logger.error("[TruthLens] TAVILY_API_KEY is not configured")
                raise TavilyConfigError("Tavily API key is not configured")

            try:
                tavily_data = await self.tavily_client.search(
                    query=clean_query,
                    max_results=top_k,
                    search_depth="advanced",
                    include_answer=True,
                    include_raw_content=False
                )
            except TavilyConfigError:
                raise
            except Exception as e:
                logger.error(f"[TruthLens] Tavily search error: {e}")
                if settings.mock_mode:
                    return self._search_local_kb(clean_query, claim_id, top_k, min_similarity, temporal_filter_year)
                raise TavilyAPIError("External source verification is temporarily unavailable") from e

            raw_results = tavily_data.get("results", []) or []
            if not raw_results:
                return []

            evidence_items: List[EvidenceItem] = []

            top_raw_score = 0.0
            if raw_results and raw_results[0].get("score") is not None:
                try:
                    top_raw_score = float(raw_results[0].get("score", 0.0))
                except (ValueError, TypeError):
                    top_raw_score = 0.70

            direct_answer = tavily_data.get("answer")
            if direct_answer and len(str(direct_answer).strip()) > 10 and top_raw_score >= 0.60:
                first_url = raw_results[0].get("url", "https://tavily.com")
                first_domain = self.tavily_client.extract_domain(first_url)
                ans_tokens = set(re.findall(r"\w+", str(direct_answer).lower()))
                q_tokens = set(re.findall(r"\w+", clean_query.lower()))
                ans_overlap = len(q_tokens.intersection(ans_tokens)) / max(1, len(q_tokens))
                ans_relevance = round(max(0.60, min(0.98, ans_overlap * 1.2)), 3)

                evidence_items.append(
                    EvidenceItem(
                        evidence_id=f"tavily_ans_{hashlib.md5(str(direct_answer).encode()).hexdigest()[:10]}",
                        claim_id=claim_id,
                        source=f"{first_domain} (via Tavily)",
                        url=first_url,
                        title=f"Tavily Synthesis: {raw_results[0].get('title', first_domain)}",
                        text=str(direct_answer).strip(),
                        relevance_score=ans_relevance,
                        authority_score=0.95,
                        publication_date=None,
                        retrieved_at=datetime.now(timezone.utc).isoformat(),
                        temporal_validity=True,
                        source_type="tavily"
                    )
                )

            for idx, r in enumerate(raw_results):
                url = r.get("url") or ""
                domain = self.tavily_client.extract_domain(url)
                title = r.get("title") or domain
                content = r.get("content") or ""
                raw_score = r.get("score")

                try:
                    relevance = round(max(0.0, min(1.0, float(raw_score))), 3) if raw_score is not None else round(max(0.70, 0.95 - (idx * 0.05)), 3)
                except (ValueError, TypeError):
                    relevance = 0.85

                credibility = self.credibility_scorer.evaluate_source(
                    source_name=domain,
                    url=url,
                    publication_date=r.get("published_date"),
                    source_type="web"
                )

                ev_id = f"tavily_{hashlib.md5(f'{url}_{idx}'.encode()).hexdigest()[:12]}"
                evidence_items.append(
                    EvidenceItem(
                        evidence_id=ev_id,
                        claim_id=claim_id,
                        source=domain,
                        url=url,
                        title=title,
                        text=content,
                        relevance_score=relevance,
                        authority_score=credibility.get("overall_credibility", 0.90),
                        publication_date=r.get("published_date"),
                        retrieved_at=datetime.now(timezone.utc).isoformat(),
                        temporal_validity=True,
                        source_type="tavily"
                    )
                )

            return evidence_items

        return self._search_local_kb(clean_query, claim_id, top_k, min_similarity, temporal_filter_year)

    def search_evidence(
        self,
        query: str,
        claim_id: Optional[str] = None,
        top_k: int = 5,
        min_similarity: float = 0.20,
        temporal_filter_year: Optional[int] = None,
        enable_multi_hop: bool = True
    ) -> List[EvidenceItem]:
        """Synchronous search for backward compatibility and offline unit tests."""
        return self._search_local_kb(
            query=query,
            claim_id=claim_id,
            top_k=top_k,
            min_similarity=min_similarity,
            temporal_filter_year=temporal_filter_year,
            enable_multi_hop=enable_multi_hop
        )

    def _search_local_kb(
        self,
        query: str,
        claim_id: Optional[str] = None,
        top_k: int = 5,
        min_similarity: float = 0.20,
        temporal_filter_year: Optional[int] = None,
        enable_multi_hop: bool = True
    ) -> List[EvidenceItem]:
        """
        Executes hybrid dense/keyword retrieval, optional multi-hop expansion, and ranking against local KB.
        """
        if not query or not query.strip() or not self.documents or not self.vectorizer:
            return []

        # 1. Primary Hybrid Search
        initial_results = self._rank_documents(query, top_k * 2)

        # 2. Multi-hop graph expansion for key entities
        expanded_docs = dict(initial_results)
        if enable_multi_hop:
            key_entities = self._extract_query_entities(query)
            for entity in key_entities:
                hop_results = self._rank_documents(entity, top_k=2)
                for doc_id, score in hop_results:
                    if doc_id not in expanded_docs:
                        expanded_docs[doc_id] = score * 0.85  # decay secondary hop score

        # 3. Filter, score credibility, and build EvidenceItem list
        evidence_items: List[EvidenceItem] = []
        for doc_id, score in sorted(expanded_docs.items(), key=lambda x: x[1], reverse=True):
            if score < min_similarity:
                continue

            doc = next((d for d in self.documents if d["id"] == doc_id), None)
            if not doc:
                continue

            # Temporal filtering if specified
            if temporal_filter_year:
                doc_text = doc.get("text", "") + " " + (doc.get("publication_date") or "")
                doc_years = [int(y) for y in re.findall(r"\b(1[6-9]\d{2}|20\d{2})\b", doc_text)]
                if doc_years and not any(abs(y - temporal_filter_year) <= 5 for y in doc_years):
                    continue

            credibility = self.credibility_scorer.evaluate_source(
                source_name=doc.get("source", "Unknown"),
                url=doc.get("url"),
                publication_date=doc.get("publication_date"),
                source_type=doc.get("source_type", "local")
            )

            evidence_items.append(
                EvidenceItem(
                    evidence_id=doc["id"],
                    claim_id=claim_id,
                    source=doc.get("source", "Reference Corpus"),
                    url=doc.get("url"),
                    title=doc.get("title"),
                    text=doc.get("text", ""),
                    relevance_score=round(min(1.0, float(score)), 3),
                    authority_score=credibility["overall_credibility"],
                    publication_date=doc.get("publication_date"),
                    retrieved_at=datetime.now(timezone.utc).isoformat(),
                    temporal_validity=True,
                    source_type=doc.get("source_type", "local")
                )
            )

            if len(evidence_items) >= top_k:
                break

        return evidence_items

    def _rank_documents(self, query: str, top_k: int) -> List[Tuple[str, float]]:
        """Calculate hybrid cosine similarity + token overlap."""
        if not self.vectorizer or self.tfidf_matrix is None:
            return []

        query_vec = self.vectorizer.transform([query])
        sim_scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        query_terms = set(re.findall(r"\w+", query.lower()))
        ranked: List[Tuple[str, float]] = []

        for idx, base_score in enumerate(sim_scores):
            doc = self.documents[idx]
            doc_terms = set(re.findall(r"\w+", (doc.get("text", "") + " " + doc.get("title", "")).lower()))

            # Keyword Jaccard term overlap
            overlap = len(query_terms.intersection(doc_terms)) / max(1, len(query_terms))
            # Hybrid fusion (70% dense/tfidf, 30% lexical overlap)
            hybrid_score = (0.70 * float(base_score)) + (0.30 * float(overlap))

            if hybrid_score > 0.05:
                ranked.append((doc["id"], hybrid_score))

        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

    def _extract_query_entities(self, query: str) -> List[str]:
        """Extract capitalized multi-word tokens for multi-hop expansion."""
        caps = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", query)
        return [c for c in caps if c.lower() not in ("the", "this", "what", "where", "when")]

    def _extract_year(self, text: str) -> Optional[int]:
        """Utility to extract year from text."""
        match = re.search(r"\b(1[6-9]\d{2}|20\d{2})\b", text)
        return int(match.group(1)) if match else None
