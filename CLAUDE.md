# CLAUDE.md — Repair-Note Triage (Honda take-home)

## What this is
Take-home for Honda Senior ML Engineer (AWS AgentCore). Due **July 16, 2026 11:59 PM ET**.
Turn free-text dealership repair notes (30-record CSV) into a field-quality analyst tool:
what's failing, how serious, warranty coverage — batch/aggregation-first.
Full brief: `docs/assignment/Honda-Technical-Take-Home-Assignment.docx` (in repo). Sample data: `data/repair_notes_sample.csv`.

## Assignment guardrails (from the brief — scope discipline)
- **Effort target: 8–12 hrs of actual build time.** Focused prototype, NOT a finished product. Prefer a clean working core loop over feature count.
- **Explicitly OUT of scope:** auth/accounts/multi-tenancy; production infra / CI-CD / real cloud deploy; exhaustive test coverage (a few meaningful tests welcome); visual polish beyond a clean usable dashboard. If short on time, cut deliberately and note "what I'd do next" in the README.
- **Evaluated on 5 axes:** (1) Technical execution — runs as documented, clean coherent code; (2) Judgment under ambiguity — stated assumptions & tradeoffs; (3) Technical & AI depth; (4) Cloud reasoning — env-driven config + credible AWS scaling story; (5) Communication — clear README + defend decisions in follow-up.
- Follow-up interview walks the code: everything shipped must be understood and defensible (drives the LLM-USAGE honesty requirement).

## Fixed stack (from the brief — do not deviate)
- Docker Compose: frontend + backend + LocalStack containers
- Frontend: Next.js or React. Backend: FastAPI (Python)
- LLM: OpenRouter free router, model `openrouter/free`, OpenAI SDK pointed at
  https://openrouter.ai/api/v1 — key/base-url/model via env vars only, `.env.example` required
- AWS: LocalStack S3 via boto3, endpoint from env var. Meaningful S3 use required
- Rate limits: ~20 req/min, **50 req/day** → cache-first design is mandatory
- Deliverables: docker-compose.yml, README (assumptions, architecture, setup, shortcuts,
  scaling + real-AWS plan), docs alongside code, LLM-USAGE.md. Zip w/o env packages →
  copilotsupport@na.honda.com. Evaluators run from clean clone exactly as README says.

## Locked architecture decisions (rationale in docs/architecture-notes.md)
1. Warranty = 4-state enum (covered/denied/undetermined/not_applicable) + denial_reason. Never boolean.
2. S3 = load-bearing extraction cache: `extractions/{note_id}.json` + metadata. Restart costs 0 LLM calls. Also the audit trail.
3. Throughput scaling target; schema prototype-scoped with explicit generalization seams.
4. One LLM call per note, retry cap 1, then needs_review=true. No agent loops (budget math: 30×3=90 > 50/day).
5. Pipeline is SCHEMA-DRIVEN: prompt constraint + response validation both load `schema/extraction_schema.json` at runtime. Never hardcode fields.
6. Structured CSV fields (note_id/date/model/model_year/mileage) are pass-through — never LLM-extracted.
7. `schema_tools` module: `--validate` ON by default (V1–V5 deterministic, exit code gates pipeline); `--discover` OFF (generation emits JSON+YAML from one internal definition).
8. Discovery = monotonic extension only: add enum values + OPTIONAL fields; never required/remove/rename. Compat proof pattern in notebook Part 3b.
9. V6 hybrid (regex + MiniLM vs semantic_descriptions in schema_spec.yaml) is ADVISORY only, never gates.
10. Discovery LLM extensible to local models via separate DISCOVERY_LLM_BASE_URL/MODEL env vars (OpenAI-compatible). Extraction uses OPENROUTER_* vars. Budgets never mix.

## Key facts about the data (planted signal)
5/30 notes = CR-V infotainment/display failures (RO-100001/6/10/16/26), MY2022–24, low mileage,
escalating to safety (backup camera). The dashboard MUST surface this cluster immediately —
subsystem × model × model_year rollup with recency + severity. It's what the evaluators look for.

## Repo layout (target)
- `eda/` — eda_schema_discovery_and_validation.ipynb + generated artifacts (done, keep as-is)
- `schema/` — extraction_schema.json (locked contract), schema_spec.yaml (record + semantic_descriptions)
- `backend/` — FastAPI: ingest, cache-check, extraction, validation, aggregation endpoints
- `frontend/` — dashboard: aggregate view first, drill-down to note + evidence_quote, needs_review queue
- `docs/` — discussion-notes.md, architecture-notes.md, build-notes.md, deploy-notes.md
  (RUNNING LOGS — append to these every session; they feed the interview project doc)
- `docker-compose.yml`, `.env.example`, `README.md`, `LLM-USAGE.md`

## Working agreement with Sunit
- Sunit drives architecture; Claude is researcher/engineer. Concise answers.
- First principles + toy examples when explaining mechanisms.
- Log every session's decisions/bugs into the four docs/ files as you go.
- RESOLVED (Session 2, Jul 14): `intermittent` added as 6th severity_flag; schema bumped to **v0.2.0**. Made *required* at this authored baseline (no cached S3 records exist yet); production discovery additions stay OPTIONAL to preserve cache compat. Contract now lives at `schema/extraction_schema.json` + `schema/schema_spec.yaml`.
- Repo now seeded from handoff: `schema/` (v0.2.0 contract + spec), `eda/` (notebook + generated_* + schema_validation_report.json), `data/repair_notes_sample.csv`, `docs/` (four running logs).
- Next step: write the SDD (spec: components, interfaces, env contract, build order for ~2 days), then build core loop: extractor+cache → aggregation → dashboard → compose → README. Clean-clone test reserved at the end.
