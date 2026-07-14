# Architecture Notes — Honda Warranty & Repair-Order Triage

## Locked decisions
| # | Decision | Rationale | Generalization seam |
|---|----------|-----------|---------------------|
| 1 | Warranty = 4-state enum (`covered/denied/undetermined/not_applicable`) + `denial_reason` | ~⅓ of notes are silent/undecided; binary forces hallucination | Reason taxonomy extends per market/regulation |
| 2 | S3 (LocalStack) as **load-bearing extraction cache** | 50 req/day budget: without cache, app can't run twice; evaluator restart must be free | S3 layout = per-note JSON + metadata → audit trail; maps 1:1 to real S3 |
| 3 | Throughput scaling target | Analyst velocity: seconds/batch vs hours manual. Not schema generalization (yet) | Schema versioning + canonical parts taxonomy noted as phase-2 |
| 4 | One LLM call per note, capped retries (1), then `needs_review` | 30 calls fits budget with retry headroom; batching = larger blast radius per malformed response | Batch mode possible later behind same interface |
| 5 | Schema derived from EDA evidence, validated pre-extraction | Contract-first; prompt is flesh on the schema skeleton | Validation module → budgeted-LLM generation module at scale |
| 6 | Structured CSV fields (note_id/date/model/year/mileage) are pass-through, never LLM-extracted | Single source of truth; no hallucination surface for known facts | — |

## Extraction schema (v0.2.0 — `schema/extraction_schema.json`, JSON Schema 2020-12)
- `complaint_summary` (str ≤200), `component_mention` (free text — seam → canonical parts taxonomy)
- `subsystem` enum (10): infotainment_electronics, hvac, powertrain, electrical_battery, body_doors, chassis_suspension, brakes, adas_safety, tires_wheels, other ("other" = drift release valve)
- `warranty_status` (4-state) + `denial_reason` (wear_item/out_of_warranty/external_cause/customer_caused/null)
- `resolution_status` enum (8): repaired, declined, escalated, monitoring, nff, parts_pending, no_defect, unclear
- `severity` (low/medium/high/critical) + `severity_flags` booleans: safety_related, vehicle_disabled, repeat_visit, customer_distress, fleet_signal, intermittent (v0.2.0)
- `confidence` (high/medium/low), `evidence_quote` (≤300, audit trail)
- `additionalProperties: false` everywhere — malformed/extra output fails validation, note goes to review queue

## Schema lifecycle
1. `01_eda_schema_discovery.ipynb` — interrogate corpus (zero LLM), produce evidence → schema authored from evidence
2. `02_schema_validation.ipynb` — V1 subsystem coverage, V2 warranty signal coverage, V3 flag coverage, V4 orphan vocabulary, V5 schema↔lexicon consistency → `schema_validation_report.json`
3. Extraction conforms to locked schema version; validation re-runs on any schema change
4. Production: validation module grows generation mode (budgeted LLM EDA — see discussion notes)

## Pipeline (target)
ingest CSV → (cache check S3) → per-note LLM extraction (OpenRouter `openrouter/free`, JSON Schema-constrained) → validate response against schema → write S3 (`extractions/{note_id}.json` + metadata) → aggregation layer (reads all cached JSONs, computes subsystem × model × year rollups) → FastAPI serves → React/Next dashboard (aggregate view first, drill-down to note + evidence_quote)

## Open decisions (next sessions)
- S3 key layout final form; whether aggregates are precomputed to S3 or computed on read
- Prompt design: schema-in-prompt + few-shot anchors for severity; robustness across router-randomized free models
- Dashboard: exact aggregate view + review-queue UX
- Real-AWS mapping section (S3→S3, compute story, optional SQS)

## Locked (Session 1, cont.) — EDA module in the project build
- Module `schema_tools` (working name) with two flags:
  - `--validate` (ON by default): runs V1–V5 against the *active* schema, writes `schema_validation_report.json`, non-zero exit on failure → can gate the extraction pipeline.
  - `--discover` (OFF by default): schema *generation* — emits BOTH artifacts (JSON Schema contract + YAML spec) rendered from one internal schema definition. Never hand-maintain two files.
- **Design requirement this imposes:** the extraction pipeline is schema-DRIVEN, not hardcoded — prompt constraint and response validation both load the active `extraction_schema.json` at runtime. Consequence: a generated (coarser) schema can run the entire project unchanged; the hand-authored + LLM-inspected schema is simply finer-grained (anchored severity, confidence/evidence semantics, curated enums). This is the live demo of the hardening story.

## Locked (Session 1, cont.) — Hybrid regex + semantic signal detection
- All regex signal families gain a semantic counterpart: MiniLM scores each note against per-enum `semantic_descriptions` now living in schema_spec.yaml (single source of truth; descriptions authored via LLM-assisted corpus inspection).
- Regex = precision on domain shorthand (OOW/NFF/BO); semantic = recall on paraphrase + breaks lexicon circularity at meaning level; the LLM extractor still owns per-note decisions.
- V6 outputs disagreement reports (semantic-top1 vs regex, both directions) + semantic coverage floor (notes far from every category). No hard thresholds on 30 unlabeled notes — ranked review tables; thresholds calibrated from labeled spot-checks at scale.

## Locked (Session 1, cont.) — Schema-locked discovery + validation independence
- Discovery has two behaviors: bootstrap (greenfield only) and EXTENSION (production default): seeded from locked schema, monotonic — may only add enum values and OPTIONAL fields. Never remove/rename/retype; new fields never `required` (would invalidate cached S3 records); promotion to required = major version + re-extraction. Diff → review gate reviews additions only. Machine-checked compat proof in notebook Part 3b (old records valid under both; new records rejected by locked).
- Validation independence: V1–V5 deterministic, gate the pipeline via exit code; V6 (hybrid semantic) strictly advisory, never a gate, absence changes nothing.

## Locked (Session 1, cont.) — Local lightweight LLM for schema discovery (extensible)
- Discovery mode may be driven by a small local LLM (e.g. Llama 3.2 1B–3B via Ollama/llama.cpp/vLLM). Structurally sound because discovery is offline, infrequent, and GATED (diff → review → monotonic extension) — imperfect proposals are tolerated by design. Extraction stays on the stronger hosted model (per-note, quality-critical, ungated).
- Benefits: no rate limits/cost for discovery, and no data egress — real (non-synthetic) repair notes never leave premises for schema work. Enterprise argument.
- Extensibility is free: local servers expose OpenAI-compatible endpoints — same client code, separate env config (DISCOVERY_LLM_BASE_URL/DISCOVERY_LLM_MODEL vs extraction's OPENROUTER_* vars). Discovery and extraction budgets/models never mix.
- Full layering: regex (deterministic validation) | embeddings (similarity/clustering) | small local LLM (cluster labeling + candidate schema proposals, gated) | hosted LLM (per-note extraction).
