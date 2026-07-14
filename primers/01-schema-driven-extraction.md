# Primer: Schema-driven extraction (the LLM call)   ·   ~8 min   ·   [AI depth]
> How one free-text repair note becomes a **validated, grounded, structured record** from a single LLM call.
> This is the heart of the assignment's AI depth.

## The concept (first principles)
The schema is a **contract**, and one contract drives three things at once:
1. **The constraint** we hand the model (structured output),
2. **The validator** we re-check the answer against,
3. **The prompt** (field meanings + the uncertainty rule come *from* the schema, not hardcoded).

The model's job is narrowed to "fill this shape, honestly." Two safety rails make it trustworthy:
- **Uncertainty contract** — anything the note doesn't support → `undetermined`/`unclear`/`null`, never guessed.
- **`evidence_quote` tripwire** — the model must quote the note verbatim to justify its answer; we check
  that quote is a real substring. A fabricated quote = a caught hallucination.

*Toy example — RO-100024* ("whining during regen braking… explained normal hybrid operation. NFF"):
→ `severity=low`, `warranty_status=not_applicable`, `resolution=no_defect`, evidence = the "normal
operation" span. Low mileage on a 2024 does **not** make it `covered` — no decision was stated.

## In the code
- `backend/prompt.py` → `build_system_prompt()` — assembles role + `schema.uncertainty_contract` +
  per-enum `semantic_descriptions` (both pulled from the schema) + the 3 severity **anchors**. Only the
  note is sent (identity fields withheld → no warranty-from-mileage temptation).
- `backend/schema_loader.py` → `response_format()` — wraps the schema as the structured-output constraint;
  its `description`s ride to the model. (`strict=False` — see Probe.)
- `backend/extract.py` → `_validate()` — the **two gates**: `jsonschema` structural check, then the
  `evidence_quote` substring tripwire.
- `backend/extract.py` → `extract_note()` — the loop: build prompt → call → validate → retry ≤ cap →
  else `needs_review` (confidence forced `low`).
- `backend/providers/openai_compat.py` → `complete_json()` — the actual call (`temperature=0`).

## Why it's built this way
→ ADR-0004 (schema-driven prompt) · SDD §6. Descriptions authored once, consumed by constraint *and*
prompt; grounding is deterministically checkable, not a self-explanation.

## Probe deeper? (pick your dive)
- 🔍 **The two-gate `_validate()`** — structural vs. semantic (substring). Why the substring check is the
  real anti-hallucination win, and why it forces `needs_review` rather than silently accepting.
- 🔍 **`strict=False` in `response_format()`** — why we *don't* use strict structured output on the free
  router (optional/nullable `denial_reason` + model variance) and lean on defensive validation instead.
- 🔍 **Anchors vs. evidence_quote** — `prompt.py` `_ANCHORS` (input calibration) vs. the per-note quote
  (output grounding). They're orthogonal; the quote never cites an anchor.
