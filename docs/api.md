# TruthGuard API Reference

TruthGuard provides a RESTful API compliant with OpenAPI 3.1. Interactive Swagger UI is hosted at `/docs`.

## Endpoints Summary

### 1. Main Analysis Pipeline
* **`POST /api/v1/analyze`**
  * **Payload**:
    ```json
    {
      "input_context": "Optional source reference",
      "llm_output": "Google was founded in 1999. The Earth revolves around the Sun.",
      "domain": "general",
      "apply_correction": true
    }
    ```
  * **Response**: Full `AnalyzeResponse` with extracted claims, multi-signal scores, verdicts, and evidence-grounded corrected output.

* **`GET /api/v1/analysis/{analysis_id}`**
  * Fetches historical analysis run and stored claim breakdowns.

### 2. Modular Claim Services
* **`POST /api/v1/claims/extract`**: Decomposes text into atomic propositions with entity/temporal tags.
* **`POST /api/v1/claims/verify`**: Runs verification on pre-decomposed claims.

### 3. Evidence & Verification Modules
* **`POST /api/v1/evidence/search`**: Queries vector and keyword indices for evidence.
* **`POST /api/v1/verification/nli`**: Natural Language Inference entailment/contradiction scoring.
* **`POST /api/v1/verification/knowledge-graph`**: Fact checking against `<Subject, Predicate, Object>` triples.
* **`POST /api/v1/verification/consensus`**: Multi-agent consensus ensemble checking.

### 4. Correction & Mitigation
* **`POST /api/v1/correction`**: Contextual rewriter applying minimal factual modifications.

### 5. Evaluation & System Health
* **`POST /api/v1/evaluation/run`**: Triggers golden benchmark runner and computes F1, accuracy, and latency metrics.
* **`GET /api/v1/evaluation/results`**: Retrieves latest benchmark telemetry.
* **`GET /api/v1/health`**: System health and configuration state.
* **`GET /api/v1/metrics`**: Observability telemetry (throughput, latency percentiles).
