"""
TruthGuard Atomic Claim Extraction & Classification Engine.

Implements:
1. Sentence segmentation with abbreviation & number boundary awareness.
2. Clause decomposition and conjunction splitting (e.g., 'and', 'but', 'while').
3. Named Entity Recognition (NER) for Persons, Organizations, Places, and Works.
4. Temporal expression detection (years, dates, chronological tokens).
5. Taxonomic classification:
   - Factual (external world facts)
   - Faithful (cross-checked against source input context)
   - Logical (internal contradictions within text)
   - Temporal (chronological orderings & dates)
   - Entity (names, products, organizations)
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.schemas.schemas import ExtractedClaim, HallucinationType


ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "jr", "sr", "vs", "etc",
    "e.g", "i.e", "st", "ave", "dept", "approx", "jan", "feb", "mar",
    "apr", "jun", "jul", "aug", "sep", "oct", "nov", "dec", "inc", "ltd", "corp"
}

YEAR_PATTERN = re.compile(r"\b(1[6-9]\d{2}|20\d{2}|2100)\b")
DATE_PATTERN = re.compile(
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2}(?:st|nd|rd|th)?,?\s+(?:1[6-9]\d{2}|20\d{2})\b",
    re.IGNORECASE,
)
MONTH_YEAR_PATTERN = re.compile(
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(?:1[6-9]\d{2}|20\d{2})\b",
    re.IGNORECASE,
)
CENTURY_PATTERN = re.compile(r"\b\d{1,2}(?:st|nd|rd|th)\s+century\b", re.IGNORECASE)

# Common entity patterns (Capitalized multi-word sequences or known entity markers)
CAPITALIZED_ENTITY_PATTERN = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b")

KNOWN_ENTITIES = {
    "albert einstein", "isaac newton", "marie curie", "charles darwin",
    "google", "microsoft", "apple", "amazon", "meta", "nasa", "spacex",
    "germany", "united states", "france", "united kingdom", "paris", "berlin",
    "london", "tokyo", "theory of relativity", "quantum mechanics", "world war ii",
    "apollo 11", "neil armstrong", "python", "qdrant", "fastapi"
}

CLAUSE_CONJUNCTIONS = [
    ", and ", "; and ", " and also ", " and subsequently ",
    ", but ", "; but ", ", while ", "; whereas "
]

# Coordinating conjunction with action verb pattern: e.g. " and developed", " and was", " and founded"
AND_VERB_PATTERN = re.compile(
    r"\s+and\s+(developed|founded|created|discovered|authored|invented|launched|became|joined|built|led|released|won|published|received|was|is|born)\b",
    re.IGNORECASE,
)


class ClaimExtractorService:
    """Production-grade claim decomposition and entity/temporal annotation service."""

    def __init__(self, settings: Optional[Any] = None) -> None:
        self.settings = settings

    def extract_claims(
        self,
        text: str,
        context: Optional[str] = None
    ) -> List[ExtractedClaim]:
        """
        Decompose text into atomic, self-contained claims.
        Annotates entities, temporal expressions, and initial taxonomy tags.
        """
        if not text or not text.strip():
            return []

        # 1. Segment sentences
        raw_sentences = self._segment_sentences(text)
        decomposed_clauses: List[Tuple[str, int, int]] = []

        # 2. Decompose compound sentences into atomic propositions
        for sent, start_idx, end_idx in raw_sentences:
            sub_clauses = self._split_compound_sentence(sent, start_idx)
            decomposed_clauses.extend(sub_clauses)

        # 3. Build ExtractedClaim objects with entity and temporal extraction
        claims: List[ExtractedClaim] = []
        for idx, (clause_text, s_idx, e_idx) in enumerate(decomposed_clauses, start=1):
            cleaned = self._clean_claim_text(clause_text)
            if not self._is_substantive_claim(cleaned):
                continue

            entities = self._extract_entities(cleaned)
            temporals = self._extract_temporals(cleaned)
            taxonomy_tag = self._classify_claim_type(cleaned, entities, temporals, context)

            claims.append(
                ExtractedClaim(
                    claim_id=f"claim_{idx:03d}",
                    text=cleaned,
                    type=taxonomy_tag,
                    entities=entities,
                    temporal_expressions=temporals,
                    char_start=s_idx,
                    char_end=e_idx,
                )
            )

        # 4. Check for internal logical contradictions among extracted claims
        self._tag_logical_contradictions(claims)

        return claims

    def _segment_sentences(self, text: str) -> List[Tuple[str, int, int]]:
        """Sentence splitter respecting abbreviations, numbers, and quotes."""
        sentences: List[Tuple[str, int, int]] = []
        current_start = 0
        i = 0
        n = len(text)

        while i < n:
            char = text[i]
            if char in ".!?":
                is_boundary = False
                rest = text[i + 1:]

                if not rest.strip():
                    is_boundary = True
                elif rest and rest[0] in " \t\n\r":
                    after_space = rest.lstrip()
                    if after_space and (after_space[0].isupper() or after_space[0] in "\"'"):
                        is_boundary = True

                # Guard against abbreviations
                if is_boundary and char == ".":
                    preceding = text[current_start:i].strip()
                    words = preceding.split()
                    if words:
                        last_token = words[-1].lower().rstrip(".")
                        if last_token in ABBREVIATIONS:
                            is_boundary = False
                    # Guard against decimals
                    if i > 0 and text[i - 1].isdigit():
                        if i + 1 < n and text[i + 1].isdigit():
                            is_boundary = False

                if is_boundary:
                    raw_segment = text[current_start:i + 1].strip()
                    if raw_segment:
                        sentences.append((raw_segment, current_start, i + 1))
                    current_start = i + 1
                    while current_start < n and text[current_start] in " \t\n\r":
                        current_start += 1
                    i = current_start
                    continue
            i += 1

        remaining = text[current_start:].strip()
        if remaining:
            sentences.append((remaining, current_start, n))

        return sentences

    def _split_compound_sentence(
        self,
        sentence: str,
        base_offset: int
    ) -> List[Tuple[str, int, int]]:
        """Splits compound clauses with coordinating conjunctions while resolving the subject."""
        results: List[Tuple[str, int, int]] = []
        parts = [sentence]

        for conj in CLAUSE_CONJUNCTIONS:
            new_parts = []
            for part in parts:
                if conj in part:
                    splits = part.split(conj, 1)
                    new_parts.extend(splits)
                else:
                    new_parts.append(part)
            parts = new_parts

        # Also check for ' and <action_verb>'
        final_parts = []
        for part in parts:
            match = AND_VERB_PATTERN.search(part)
            if match:
                s1 = part[:match.start()].strip()
                # verb starts at match.group(1)
                verb = match.group(1)
                s2 = part[match.start(1):].strip()
                if s1:
                    final_parts.append(s1)
                if s2:
                    final_parts.append(s2)
            else:
                final_parts.append(part)
        parts = final_parts

        if len(parts) == 1:
            return [(sentence, base_offset, base_offset + len(sentence))]

        # Resolve omitted subject in subsequent split clauses
        first_clause = parts[0].strip()
        primary_subject = self._extract_leading_subject(first_clause)

        for i, part in enumerate(parts):
            clause = part.strip()
            if not clause:
                continue
            if not clause.endswith((".", "!", "?")):
                clause += "."
            
            # If secondary clause starts with a verb phrase and has no subject, prepend primary subject
            if i > 0 and primary_subject and self._starts_with_verb(clause):
                resolved_clause = f"{primary_subject} {clause[0].lower() + clause[1:]}"
            else:
                resolved_clause = clause

            c_start = sentence.find(part)
            start_idx = base_offset + (c_start if c_start >= 0 else 0)
            end_idx = start_idx + len(part)

            results.append((resolved_clause, start_idx, end_idx))

        return results if results else [(sentence, base_offset, base_offset + len(sentence))]

    def _extract_leading_subject(self, clause: str) -> Optional[str]:
        """Extract leading noun phrase / subject from clause."""
        words = clause.split()
        if not words:
            return None
        cap_match = CAPITALIZED_ENTITY_PATTERN.match(clause)
        if cap_match:
            return cap_match.group(0)
        if len(words) >= 2 and words[0].lower() in ("the", "a", "an"):
            return f"{words[0]} {words[1]}"
        return None

    def _starts_with_verb(self, clause: str) -> bool:
        """Heuristic check if a clause begins with a past-tense / present verb."""
        first_word = clause.split()[0].lower() if clause.split() else ""
        verb_markers = (
            "was", "is", "developed", "created", "discovered", "founded", "won",
            "published", "invented", "authored", "launched", "became", "joined",
            "built", "led", "released", "announced", "received"
        )
        return first_word in verb_markers or first_word.endswith("ed")

    def _clean_claim_text(self, text: str) -> str:
        """Format and ensure proper punctuation."""
        cleaned = text.strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        if cleaned and cleaned[-1] not in ".!?":
            cleaned += "."
        return cleaned

    def _is_substantive_claim(self, text: str) -> bool:
        """Filter out conversational pleasantries, questions, and non-claims."""
        if not text or len(text) < 10:
            return False
        words = text.split()
        if len(words) < 3:
            return False
        lower = text.lower().strip()
        if lower.endswith("?"):
            return False
        skip_phrases = (
            "hello", "hi ", "hey", "sure", "of course", "i hope", "in my opinion",
            "let me know", "feel free", "as an ai", "thank you", "thanks",
            "i would be glad", "glad to help", "happy to help", "how can i help",
            "hope you are doing well"
        )
        if any(phrase in lower for phrase in skip_phrases):
            return False
        return True

    def _extract_entities(self, text: str) -> List[str]:
        """Extract named entities using pattern matching and gazetteer lookup."""
        entities: Set[str] = set()

        # Gazetteer check
        lower = text.lower()
        for known in KNOWN_ENTITIES:
            if known in lower:
                entities.add(known.title())

        # Capitalized sequences check
        matches = CAPITALIZED_ENTITY_PATTERN.findall(text)
        for m in matches:
            if m.lower() not in ("the", "this", "that", "in", "on", "at", "when", "after", "it", "they"):
                entities.add(m)

        # Common nouns acting as primary subjects: e.g. "The company", "The project"
        sub_match = re.match(r"^(The|A)\s+([A-Za-z]+)", text, re.IGNORECASE)
        if sub_match:
            entities.add(f"{sub_match.group(1).title()} {sub_match.group(2).lower()}")

        return sorted(list(entities))

    def _extract_temporals(self, text: str) -> List[str]:
        """Extract explicit temporal expressions (years, full dates, centuries)."""
        temporals: Set[str] = set()
        for y in YEAR_PATTERN.findall(text):
            temporals.add(y)
        for d in DATE_PATTERN.findall(text):
            temporals.add(d)
        for my in MONTH_YEAR_PATTERN.findall(text):
            temporals.add(my)
        for c in CENTURY_PATTERN.findall(text):
            temporals.add(c)
        return sorted(list(temporals))

    def _classify_claim_type(
        self,
        claim_text: str,
        entities: List[str],
        temporals: List[str],
        context: Optional[str]
    ) -> HallucinationType:
        """Assign preliminary taxonomic category based on features."""
        if temporals:
            return HallucinationType.TEMPORAL
        if len(entities) >= 2:
            return HallucinationType.ENTITY
        if context:
            return HallucinationType.FAITHFUL
        return HallucinationType.FACTUAL

    def _tag_logical_contradictions(self, claims: List[ExtractedClaim]) -> None:
        """Scan claims extracted from the same response for mutually contradictory facts."""
        for i in range(len(claims)):
            for j in range(i + 1, len(claims)):
                c1 = claims[i]
                c2 = claims[j]

                # Check for year conflicts for the same subject or overlapping nouns
                common_entities = set(e.lower() for e in c1.entities).intersection(set(e.lower() for e in c2.entities))
                has_year_conflict = (
                    bool(c1.temporal_expressions) and bool(c2.temporal_expressions)
                    and set(c1.temporal_expressions) != set(c2.temporal_expressions)
                )

                if (common_entities or "the company" in c1.text.lower() and "the company" in c2.text.lower()) and has_year_conflict:
                    if any(k in c1.text.lower() and k in c2.text.lower() for k in ("founded", "born", "launched", "created", "died")):
                        c1.type = HallucinationType.LOGICAL
                        c2.type = HallucinationType.LOGICAL
