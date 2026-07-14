"""Typed environment configuration (fail-fast).

Every environment-specific value — LLM provider/key, AWS endpoint, model, budget — is read here from
the environment (or a local ``.env``) into a typed ``Settings`` object. This is the *single* place the
environment is read; the rest of the app imports ``get_settings()``. It fails loudly at startup if a
required var for the selected provider is missing, so a clean-clone run errors clearly instead of dying
deep inside a request. Because nothing is hardcoded, the same code targets real AWS / a different LLM by
changing config only (the brief's env-driven-config requirement).
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal, Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- LLM provider seam (Decision F / ADR-0007) ---
    llm_provider: Literal["openrouter", "bedrock", "vllm"] = "openrouter"
    # OpenAI-compatible providers (OpenRouter, vLLM) share these three:
    openrouter_api_key: Optional[str] = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "openrouter/free"
    # Bedrock (Phase 2) — managed Claude on AWS. Dedicated creds so they never clash with the
    # LocalStack dummy creds used for S3 (Bedrock is REAL AWS).
    bedrock_model_id: Optional[str] = None
    bedrock_aws_access_key_id: Optional[str] = None
    bedrock_aws_secret_access_key: Optional[str] = None
    bedrock_aws_region: str = "us-east-1"
    # Optional discovery LLM — budget NEVER mixed with extraction (locked #10):
    discovery_llm_base_url: Optional[str] = None
    discovery_llm_model: Optional[str] = None

    # --- AWS / LocalStack (endpoint from env → same code hits real S3 by dropping it) ---
    aws_endpoint_url: str = "http://localhost:4566"
    s3_bucket: str = "repair-triage"
    aws_access_key_id: str = "test"
    aws_secret_access_key: str = "test"
    aws_region: str = "us-east-1"
    ingest_queue_url: Optional[str] = None  # SQS ingest queue (Decision G / ADR-0008)

    # --- schema-driven pipeline (locked #5) ---
    schema_path: str = "schema/extraction_schema.json"
    schema_spec_path: str = "schema/schema_spec.yaml"
    data_csv_path: str = "data/repair_notes_sample.csv"

    # --- budget / throttle (locked #4) ---
    max_requests_per_min: int = 20
    max_requests_per_day: int = 50
    retry_cap: int = 1
    worker_concurrency: int = 4

    @model_validator(mode="after")
    def _require_provider_creds(self) -> "Settings":
        """Fail fast if the selected provider is missing its required credentials."""
        if self.llm_provider == "openrouter" and not self.openrouter_api_key:
            raise ValueError("LLM_PROVIDER=openrouter requires OPENROUTER_API_KEY.")
        if self.llm_provider == "bedrock" and not self.bedrock_model_id:
            raise ValueError("LLM_PROVIDER=bedrock requires BEDROCK_MODEL_ID (+ AWS creds).")
        # vllm: a local server usually needs no key; base_url is pointed at it via OPENROUTER_BASE_URL.
        return self


@lru_cache
def get_settings() -> Settings:
    """Cached singleton — the environment is read once."""
    return Settings()
