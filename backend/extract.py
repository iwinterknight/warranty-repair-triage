"""The core extraction loop (ADR-0002 / ADR-0004): cache-check → LLM → validate → evidence tripwire → S3.

One LLM call per note, retry ≤ ``retry_cap``, then ``needs_review``. Every record carries a provenance
``meta`` block. Restart-safe: a cached record whose ``schema_version`` + ``note_sha256`` match skips the
LLM entirely (zero budget).

Persistence rule: we write a record only when the LLM actually returned a candidate (valid *or* invalid →
a real needs_review). Transient failures with no candidate (budget exhausted, network error) are NOT
cached, so they are retried on the next run rather than frozen as a false cache hit.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Optional

import jsonschema

from .budget import BudgetExceeded, BudgetGuard
from .prompt import build_system_prompt, build_user_prompt, prompt_version
from .providers import LLMClient
from .schema_loader import LoadedSchema
from .store_s3 import S3Store


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_json(raw: str) -> dict[str, Any]:
    """Tolerate a ```json fenced block from less-obedient free-router models."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.DOTALL).strip()
    return json.loads(raw)


def _validate(extraction: dict[str, Any], note_text: str, json_schema: dict[str, Any]) -> tuple[bool, str]:
    """Two gates: structural conformance, then the evidence_quote substring tripwire."""
    try:
        jsonschema.validate(extraction, json_schema)
    except jsonschema.ValidationError as e:
        return False, f"schema:{e.message[:80]}"
    quote = extraction.get("evidence_quote", "")
    if quote and quote not in note_text:
        return False, "evidence_quote_not_substring"
    return True, "pass"


def _is_cache_hit(existing: dict[str, Any], schema: LoadedSchema, note_sha: str) -> bool:
    # Provenance fields (model/prompt_version/git_sha) are deliberately NOT part of this check (ADR-0002).
    meta = existing.get("meta", {})
    return meta.get("schema_version") == schema.version and meta.get("note_sha256") == note_sha


def extract_note(
    note_id: str,
    technician_note: str,
    passthrough: dict[str, Any],
    *,
    store: S3Store,
    budget: BudgetGuard,
    client: LLMClient,
    schema: LoadedSchema,
    retry_cap: int = 1,
) -> dict[str, Any]:
    note_sha = _sha256(technician_note)

    # 1. Cache-check — schema_version + note_sha256 must match current.
    existing = store.get_extraction(note_id)
    if existing and _is_cache_hit(existing, schema, note_sha):
        existing.setdefault("meta", {})["from_cache"] = True
        return existing

    system = build_system_prompt(schema)
    user = build_user_prompt(technician_note)
    response_format = schema.response_format()

    extraction: Optional[dict[str, Any]] = None
    validation = "not_attempted"
    attempts = 0

    # 2. Call → validate → (retry ≤ cap). Only a real candidate response gets persisted.
    for attempt in range(retry_cap + 1):
        attempts = attempt + 1
        try:
            budget.check_daily()
        except BudgetExceeded as e:
            validation = f"budget:{e}"
            break
        budget.throttle()
        try:
            raw = client.complete_json(system, user, response_format)
            budget.record_call()
            candidate = _parse_json(raw)
        except Exception as e:  # network / JSON parse error → retry if attempts remain
            validation = f"error:{type(e).__name__}"
            continue
        ok, reason = _validate(candidate, technician_note, schema.json_schema)
        extraction, validation = candidate, reason
        if ok:
            break

    needs_review = validation != "pass"
    if needs_review and extraction is not None:
        extraction["confidence"] = "low"  # failed tripwire/structure → force into the review queue

    record = {
        "note_id": note_id,
        "technician_note": technician_note,  # kept for drill-down + evidence-quote highlighting in the UI
        "passthrough": passthrough,
        "extraction": extraction,
        "meta": {
            "schema_version": schema.version,
            "note_sha256": note_sha,
            "model": client.model,
            "prompt_version": prompt_version(schema),
            "git_sha": os.environ.get("GIT_SHA", "unknown"),
            "attempts": attempts,
            "validation": validation,
            "needs_review": needs_review,
            "extracted_at": _now_iso(),
            "from_cache": False,
        },
    }

    # 3. Persist only real candidates (valid or invalid). Transient no-candidate failures stay uncached.
    if extraction is not None:
        store.put_extraction(note_id, record)
    return record
