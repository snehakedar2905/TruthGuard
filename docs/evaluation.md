# TruthGuard Evaluation & Benchmarking Methodology

## 1. Automated Golden Benchmark

The automated evaluation harness evaluates TruthGuard across 5 core hallucination archetypes from `data/evaluation/benchmark_dataset.json`:

1. **Factual Hallucination**: Directly contradicted by verified real-world knowledge (e.g. incorrect founding dates, false scientific claims).
2. **Faithful Hallucination**: Inconsistent with the provided source context.
3. **Logical Hallucination**: Internal mutual contradictions within the same generated text.
4. **Temporal Hallucination**: Erroneous chronological sequencing or timestamp discrepancies.
5. **Entity Hallucination**: Fabricated people, organizations, or non-existent citations.

### Metrics Tracked:
* **Claim Extraction F1**: Evaluates precision and recall of atomic proposition identification.
* **Hallucination Detection F1**: Evaluates classification of non-factual or ungrounded assertions.
* **Verification Accuracy**: Overall correct classification across all test cases.
* **Correction Accuracy**: Semantic preservation and factual validity of rewritten text.
* **False Positive Rate (FPR) & False Negative Rate (FNR)**.
* **P50 & P95 Latency**: Validating the $< 5.0\text{s}$ SLA.

## 2. Human Evaluation Protocol

TruthGuard includes a structured qualitative audit protocol rated on a 1–5 scale:
1. **Claim Extraction Quality**: Completeness and self-containment of split claims.
2. **Evidence Relevance**: Semantic alignment of retrieved passages.
3. **Evidence Credibility**: Source authority and trustworthiness.
4. **Verdict Correctness**: Accuracy of categorical classification.
5. **Correction Correctness**: Precision of the evidence-grounded rewrite.
6. **Explanation Quality**: Interpretability and transparency of the "WHY THIS VERDICT?" rationale.
