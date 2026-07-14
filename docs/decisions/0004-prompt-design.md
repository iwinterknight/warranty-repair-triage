# ADR-0004: Schema-driven prompt design (Decision C)
- Status: Accepted — 2026-07-14
- Deciders: Sunit, Claude
- Related: SDD §6 · locked decisions #5, #6

## Context
Repair notes are out-of-domain shorthand; `openrouter/free` routes to models with uneven schema adherence;
there are no labels; and we must not hallucinate.

## Decision
- **Field/enum descriptions are the semantic ground truth**, authored once in the schema and consumed by
  **both** the `json_schema` constraint (`extraction_schema.json`) **and** the prompt (`schema_spec.yaml`
  `semantic_descriptions` for the calibration-sensitive enums).
- **Uncertainty contract**: unsupported → `undetermined`/`unclear`/`null`, never guessed. Passthrough
  fields (note_id/date/model/year/mileage) are never sent to the LLM.
- **Structured outputs + defensive `jsonschema` validation** (belt and suspenders) → fail → retry ≤1 → needs_review.
- **Few-shot severity anchors** (2–3) calibrate the ordinal without labels.
- **`evidence_quote` must be a verbatim substring** → deterministic anti-hallucination tripwire.

## Alternatives
- **Free-form prompt with hardcoded fields** — drifts from the schema; rejected (breaks schema-driven).
- **Zero-shot NLI / generic NER** — wrong for OOD shorthand, uncalibrated scores; rejected in EDA.

## Consequences
- + Grounded, auditable, calibrated extraction from one LLM call.
- − Few-shot inflates *tokens*, not *requests* — free under the 50/day request cap.
