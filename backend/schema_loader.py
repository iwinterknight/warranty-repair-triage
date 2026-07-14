"""Load the active extraction schema + spec at runtime (schema-driven — locked #5, ADR-0004).

Nothing about the fields is hardcoded elsewhere: the LLM *constraint*, the response *validator*, and the
*aggregator* all read shape and semantics from here. Swapping ``SCHEMA_PATH`` (e.g. to the coarse
``eda/generated_extraction_schema.json``) retargets the whole app — that's the hardening demo.

Two carriers of meaning, both loaded here (Decision C):
  * ``extraction_schema.json`` — the JSON Schema; its ``description``s ride into the structured-output
    constraint and the validator.
  * ``schema_spec.yaml`` — richer ``semantic_descriptions`` per enum (injected into the prompt for
    calibration-sensitive fields), the passthrough field list, and the uncertainty contract.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from .config import get_settings


@dataclass(frozen=True)
class LoadedSchema:
    version: str                       # authoritative schema_version (stamped into every record's meta)
    json_schema: dict[str, Any]        # the JSON Schema — constraint + defensive validation
    spec: dict[str, Any]               # schema_spec.yaml — semantics, passthrough, contract
    passthrough_fields: list[str]      # trusted CSV fields NEVER sent to the LLM (locked #6)
    uncertainty_contract: str          # injected verbatim into the prompt (Decision C)

    def response_format(self) -> dict[str, Any]:
        """OpenAI-style structured-output constraint — carries the field descriptions to the model.

        ``strict=False`` on purpose: our schema has an optional/nullable ``denial_reason``, and the free
        router's varied models reject strict mode's "every field required" rule. The constraint is
        best-effort guidance; ``extract._validate`` re-checks defensively on return (belt and suspenders).
        """
        return {
            "type": "json_schema",
            "json_schema": {
                "name": self.json_schema.get("title", "Extraction"),
                "schema": self.json_schema,
                "strict": False,
            },
        }

    def semantic_descriptions(self) -> dict[str, dict[str, str]]:
        """Per-enum meanings for the calibration-sensitive fields → injected into the prompt."""
        out: dict[str, dict[str, str]] = {}
        for field, spec in self.spec.get("extracted_fields", {}).items():
            if isinstance(spec, dict) and "semantic_descriptions" in spec:
                out[field] = spec["semantic_descriptions"]
        return out


@lru_cache
def load_schema() -> LoadedSchema:
    s = get_settings()
    json_schema = json.loads(Path(s.schema_path).read_text(encoding="utf-8"))
    spec = yaml.safe_load(Path(s.schema_spec_path).read_text(encoding="utf-8"))
    return LoadedSchema(
        version=str(spec.get("schema_version", "unknown")),
        json_schema=json_schema,
        spec=spec,
        passthrough_fields=list(spec.get("identity_passthrough", {}).get("fields", [])),
        uncertainty_contract=str(spec.get("uncertainty_contract", "")).strip(),
    )
