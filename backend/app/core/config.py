"""
TruthGuard Core Configuration.

Loads environment variables with Pydantic Settings.
Configures database, model adapters, domain profiles, and verification weights.
"""

from __future__ import annotations
import json
from typing import Any, Dict, List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class DomainThresholds:
    """Configurable domain validation parameters."""
    
    DEFAULTS: Dict[str, Dict[str, float]] = {
        "healthcare": {
            "support_threshold": 0.95,
            "uncertainty_threshold": 0.80,
            "contradiction_threshold": 0.05,
            "min_source_authority": 0.85,
        },
        "legal": {
            "support_threshold": 0.92,
            "uncertainty_threshold": 0.75,
            "contradiction_threshold": 0.08,
            "min_source_authority": 0.80,
        },
        "scientific": {
            "support_threshold": 0.90,
            "uncertainty_threshold": 0.70,
            "contradiction_threshold": 0.10,
            "min_source_authority": 0.75,
        },
        "education": {
            "support_threshold": 0.85,
            "uncertainty_threshold": 0.65,
            "contradiction_threshold": 0.15,
            "min_source_authority": 0.60,
        },
        "journalism": {
            "support_threshold": 0.85,
            "uncertainty_threshold": 0.65,
            "contradiction_threshold": 0.15,
            "min_source_authority": 0.65,
        },
        "general": {
            "support_threshold": 0.80,
            "uncertainty_threshold": 0.60,
            "contradiction_threshold": 0.20,
            "min_source_authority": 0.50,
        },
    }


class Settings(BaseSettings):
    """Application settings and configuration parameters."""

    # Project Information
    project_name: str = "TruthGuard"
    app_env: str = "development"
    debug: bool = True
    api_v1_str: str = "/api/v1"
    secret_key: str = "truthguard-development-secret-key-change-in-production"

    # Database & Storage
    database_url: str = Field(default="sqlite:///./truthguard.db")
    vector_db_url: Optional[str] = None
    vector_collection_name: str = "truthguard_evidence"

    # Mock Mode (runs deterministic local offline verification if explicitly enabled)
    mock_mode: bool = False

    # LLM Provider Configuration
    llm_provider: str = "openai"
    llm_api_key: Optional[str] = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"

    # Search Provider Configuration (Tavily Web Search)
    search_provider: str = "tavily"
    search_api_key: Optional[str] = None
    tavily_api_key: Optional[str] = None

    # Embedding & NLI Models
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    nli_model: str = "cross-encoder/nli-deberta-v3-small"

    # Knowledge Graph
    wikidata_enabled: bool = True
    local_kg_path: str = "data/knowledge_graph/facts.json"

    # Verification Weights
    weight_nli: float = 0.30
    weight_retrieval: float = 0.20
    weight_credibility: float = 0.15
    weight_knowledge_graph: float = 0.15
    weight_consensus: float = 0.10
    weight_temporal: float = 0.10

    # Operational Guardrails
    request_timeout_seconds: float = 5.0
    max_input_length: int = 10000
    retention_enabled: bool = False

    # SMS Gateway Provider Configuration
    sms_provider: str = "twilio"
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    sms_gateway_url: Optional[str] = None
    sms_api_key: Optional[str] = None

    # Security & CORS
    cors_origins: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str) and v.startswith("["):
            return json.loads(v)
        elif isinstance(v, list):
            return v
        return ["*"]

    @property
    def is_llm_configured(self) -> bool:
        """Check if an active external LLM key is configured."""
        return bool(self.llm_api_key and self.llm_api_key.strip() and not self.mock_mode)

    @property
    def effective_tavily_api_key(self) -> Optional[str]:
        """Resolve TAVILY_API_KEY or SEARCH_API_KEY securely from environment."""
        key = self.tavily_api_key or self.search_api_key
        return key.strip() if key and key.strip() else None

    @property
    def is_search_configured(self) -> bool:
        """Check if external web search provider is configured."""
        return bool(self.effective_tavily_api_key and not self.mock_mode)

    def get_domain_thresholds(self, domain: str) -> Dict[str, float]:
        """Fetch verification thresholds for a given domain."""
        norm_domain = domain.lower().strip()
        return DomainThresholds.DEFAULTS.get(norm_domain, DomainThresholds.DEFAULTS["general"])

    model_config = {
        "env_file": (".env", "../.env", "backend/.env"),
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


settings = Settings()
