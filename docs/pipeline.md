# TruthGuard Pipeline & State Transitions

## End-to-End Execution Flow

```text
Input (Context + LLM Output)
   ↓
[Claim Extraction] → Segments sentences, resolves subjects, extracts entities & dates
   ↓
[Hybrid Retrieval] → Dense + BM25 search across local corpus, knowledge store, and web
   ↓
[Concurrent Multi-Signal Scoring]
   ├── NLI Entailment: Premise/Hypothesis comparison
   ├── KG Triples: Fact existence & temporal consistency
   ├── Consensus Ensemble: Multi-verifier agreement
   └── Credibility: Authority, domain reputation & recency
   ↓
[Bayesian Verdict Aggregation] → Weighted fusion + domain threshold gating
   ↓
[Constrained Correction Engine] → In-place factual substitution of refuted spans
   ↓
Corrected Response + Structured Audit Report (<5s Latency)
```

## Configurable Fusion Weights

The composite verification score is computed as:

$$\text{Score} = w_1 \cdot \text{NLI} + w_2 \cdot \text{Retrieval} + w_3 \cdot \text{Credibility} + w_4 \cdot \text{KG} + w_5 \cdot \text{Consensus} + w_6 \cdot \text{Temporal}$$

Default weights:
* $w_1 = 0.30$ (NLI)
* $w_2 = 0.20$ (Retrieval Relevance)
* $w_3 = 0.15$ (Source Credibility)
* $w_4 = 0.15$ (Knowledge Graph)
* $w_5 = 0.10$ (Consensus Ensemble)
* $w_6 = 0.10$ (Temporal Match)

## Domain Threshold Calibration

| Domain Profile | Support Threshold | Uncertainty Threshold | Contradiction Cutoff | Minimum Authority |
| :--- | :--- | :--- | :--- | :--- |
| **Healthcare** | $\ge 0.95$ | $0.80$ | $0.05$ | $0.85$ |
| **Legal** | $\ge 0.92$ | $0.75$ | $0.08$ | $0.80$ |
| **Scientific** | $\ge 0.90$ | $0.70$ | $0.10$ | $0.75$ |
| **Education** | $\ge 0.85$ | $0.65$ | $0.15$ | $0.60$ |
| **Journalism** | $\ge 0.85$ | $0.65$ | $0.15$ | $0.65$ |
| **General** | $\ge 0.80$ | $0.60$ | $0.20$ | $0.50$ |
