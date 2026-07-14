"""Build the schema-driven extraction prompt (Decision C / ADR-0004).

The prompt is *flesh on the schema skeleton*: the uncertainty contract, the per-enum semantic descriptions,
and the passthrough rule all come FROM the loaded schema — nothing about the fields is hardcoded here.
Few-shot severity anchors calibrate the ordinal without labels. Only the ``technician_note`` is sent to the
LLM; the passthrough identity fields never reach it (locked #6), which also removes the temptation to infer
warranty coverage from mileage/age.
"""
from __future__ import annotations

import hashlib

from .schema_loader import LoadedSchema

# Curated severity anchors (SDD Decision C) — real notes RO-100024/06/26, calibrating the ordinal.
_ANCHORS = [
    ("cust concerned about whining/whir noise during regen braking. explained normal hybrid operation. "
     "NFF, no repair needed.", "low", "normal operation explained; no defect, no safety impact"),
    ("bluetooth keeps disconnecting and screen froze once. reprogrammed audio unit per TSB. seems ok now",
     "medium", "a real defect, driveable, not safety-related"),
    ("screen reboots + backup camera failed to display once when in reverse. safety concern noted. "
     "reflashed audio/nav unit.", "high", "a safety system (backup camera) failed → safety_related"),
]


def _render_semantics(schema: LoadedSchema) -> str:
    lines: list[str] = []
    for field, values in schema.semantic_descriptions().items():
        lines.append(f"- {field}:")
        for value, meaning in values.items():
            lines.append(f"    - {value}: {meaning}")
    return "\n".join(lines)


def _render_anchors() -> str:
    return "\n".join(f'- "{note}" -> severity={sev}  ({why})' for note, sev, why in _ANCHORS)


def build_system_prompt(schema: LoadedSchema) -> str:
    return (
        "You are a warranty & repair-order triage analyst. Extract structured fields from ONE dealership "
        "repair note into the provided JSON schema. Output ONLY the JSON object.\n\n"
        f"Uncertainty contract: {schema.uncertainty_contract}\n\n"
        "The vehicle identity (note_id, date, model, model_year, mileage) is known separately — do NOT "
        "restate it. Do NOT infer warranty coverage from mileage or age; only an explicit determination in "
        "the note sets warranty_status (otherwise 'undetermined').\n\n"
        "evidence_quote MUST be copied verbatim (an exact substring) from the note and should justify the "
        "subsystem and severity.\n\n"
        "Choose the enum value whose meaning fits the note:\n"
        f"{_render_semantics(schema)}\n\n"
        "Severity is a judgment — calibrate with these anchors:\n"
        f"{_render_anchors()}\n"
    )


def build_user_prompt(technician_note: str) -> str:
    return f'Repair note:\n"{technician_note}"'


def prompt_version(schema: LoadedSchema) -> str:
    """Hash of the composed system prompt → provenance stamp (ties extraction behavior to a version)."""
    return "p_" + hashlib.sha256(build_system_prompt(schema).encode("utf-8")).hexdigest()[:10]
