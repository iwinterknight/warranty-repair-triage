# SDD — Warranty & Repair-Order Triage

Spec-driven design for the Honda take-home. Companion to the locked architecture in
[`CLAUDE.md`](../CLAUDE.md) and [`architecture-notes.md`](architecture-notes.md); this doc turns those
decisions into components, interfaces, an env contract, and a ~2-day build order.

**Status:** **RATIFIED — all decisions A–G accepted (Session 2 architecting phase; see
`docs/discussion-notes.md`). Architecture is closed; ready for the build phase.** Sections marked
**⟐ DECISION** carry the accepted choice + the alternative considered. A–D were Session 1's open questions
(A accepted; B, D refined by E; C ratified as written); E–G were pitched, polished, and ratified by Sunit
in Session 2. Everything else follows from the 10 locked decisions and is not re-litigated here.

---

## 1. Goal & shape

Turn a 30-row CSV of free-text dealership repair notes into an analyst tool that surfaces *what's
failing, how serious, and warranty coverage* — **aggregation-first**. The single evaluated outcome: the
dashboard immediately surfaces the planted **CR-V infotainment cluster** (RO-100001/6/10/16/26, MY2022–24,
low mileage, escalating to a backup-camera safety concern).

Everything is a consequence of two forcing functions:
- **Budget:** OpenRouter free tier ≈ 20 req/min, **50 req/day**. ⇒ cache-first is mandatory; one LLM
  call per note; retry cap 1; no agent loops.
- **Ambiguity:** the schema is the contract. Unparseable / low-confidence notes go to a **needs-review**
  queue, never guessed.

## 2. Component map

```
warranty-repair-triage/
├─ schema/                 # the contract (v0.2.0) — loaded at runtime, never hardcoded
│  ├─ extraction_schema.json     # JSON Schema 2020-12, RepairNoteExtraction
│  └─ schema_spec.yaml           # human spec + per-enum semantic_descriptions
├─ eda/                    # done: notebook + generated_* (coarse schema) + validation report
├─ data/repair_notes_sample.csv
├─ schema_tools/           # CLI instrument (Python)
│  ├─ validate.py                # V1–V5 corpus↔schema coverage; exit code gates the pipeline
│  └─ discover.py                # OFF by default; emits JSON+YAML from ONE internal definition
├─ backend/               # FastAPI
│  ├─ config.py                  # env → typed settings; fail-fast on missing required vars
│  ├─ schema_loader.py           # loads active schema + version at runtime
│  ├─ store_s3.py                # boto3 cache repo (LocalStack endpoint from env)
│  ├─ providers/                 # LLM_PROVIDER seam (Decision F): one LLMClient interface
│  │   ├─ openai_compat.py        #   OpenRouter + vLLM (base_url/model/key)
│  │   └─ bedrock.py              #   Claude on AWS (boto3 converse)
│  ├─ budget.py                  # per-minute throttle + daily ledger (S3-backed)
│  ├─ extract.py                 # cache-check → LLM → validate → S3 write
│  ├─ query_engine.py            # Decision E: query-object grammar → parameterized DuckDB SQL
│  ├─ ingest.py                  # Decision G: POST /ingest → enqueue SQS + write job manifest
│  ├─ worker.py                  # Decision G: SQS consumer → extract → DuckDB insert → job status
│  └─ app.py                     # routes
├─ frontend/              # React (Vite) + Nivo + CSS tables — thin client over the backend
├─ docker-compose.yml     # frontend + backend + localstack
├─ .env.example
├─ README.md · LLM-USAGE.md
```

**Schema-driven, not hardcoded (locked decision #5).** `extract.py` builds the LLM constraint from
`schema_loader` and validates the response against the *same* loaded schema; `aggregate.py` reads enum
values from it. Swapping `SCHEMA_PATH` to `eda/generated_extraction_schema.json` (the coarse auto-schema)
runs the whole app unchanged — that's the live hardening demo.

## 3. Data flow

```
CSV ──▶ schema_tools --validate (gate: nonzero exit aborts) 
    ──▶ for each note:
          passthrough fields (note_id/date/model/model_year/mileage)  ── never sent to LLM
          cache-check S3  ──hit──▶ reuse (0 budget)
                          ──miss─▶ throttle+budget check ─▶ LLM (schema-constrained)
                                   ─▶ structural validate ─▶ substring-check evidence_quote
                                        ok   ─▶ write extractions/{note_id}.json (+ metadata)
                                        fail ─▶ retry ≤1 ─▶ still fail: needs_review=true, write anyway
    ──▶ aggregate.py reads all extractions/*.json ─▶ rollups + priority score
    ──▶ FastAPI serves ─▶ dashboard (aggregate → drill-down → review queue)
```

Restart-safety: a re-run finds every note cached ⇒ **zero** LLM calls (evaluator restart is free).

## 4. ⟐ DECISION A — S3 key layout

**Recommend:** flat, note-addressed records with an in-record version guard.
```
s3://{S3_BUCKET}/
  extractions/{note_id}.json     # extraction fields + passthrough + metadata
  _budget/{YYYY-MM-DD}.json       # daily call ledger (survives restart → enforces 50/day)
```
Record shape:
```json
{ "note_id": "RO-100001", "passthrough": {…}, "extraction": {…schema fields…},
  "meta": { "schema_version": "0.2.0", "note_sha256": "…", "model": "openrouter/free",
            "prompt_version": "…", "git_sha": "…",
            "attempts": 1, "validation": "pass", "needs_review": false, "extracted_at": "…" } }
```
Cache hit requires `schema_version` **and** `note_sha256` to match current ⇒ a schema bump or an edited
note transparently forces re-extraction; otherwise reuse. The per-object `meta` block **is** the audit
trail (locked decision #2).

**Provenance stamp (git ↔ runtime bridge — Topic B).** `meta` also carries `prompt_version` and `git_sha`
so any output traces back to the exact code commit, schema version, and prompt that produced it — the
alignment of code / design / LLM-use histories, made auditable. Two implementation details left open for
the build (don't over-decide now):
- `prompt_version` — a hash of the versioned prompt template (template lives in-repo; `git blame` ties
  extraction behavior to a commit). Exact hashing scheme decided at `extract.py`.
- `git_sha` — the build's commit. Baked at image build (build arg / env) vs. read at runtime: decided when
  we write the Dockerfile; either way it's env-injected, never hardcoded.
These are metadata only — they do **not** participate in the cache-hit check (which stays `schema_version`
+ `note_sha256`), so a rebuild at the same schema/prompt does not needlessly invalidate the cache.

*Alternative:* version in the path (`extractions/{schema_version}/{note_id}.json`). Cleaner isolation but
aggregation must know which version prefix to read, and it scatters the corpus. Rejected for the prototype
— the in-record guard gives the same safety with a single flat prefix to list.

## 5. ⟐ DECISION B — Aggregates: compute-on-read vs precompute-to-S3

**Recommend:** **compute-on-read** for the prototype. 30 records × a handful of rollups is microseconds;
it's always fresh and has zero staleness surface. Seam noted for scale: at 10K+ notes, precompute
`aggregates/subsystem_rollup.json` to S3 at end-of-extraction and serve that. Documented in README scaling
section, not built now.

*Alternative:* precompute now. Rejected — adds an invalidation problem (when does the aggregate go stale?)
for no prototype benefit.

> **Refined by Decision E:** compute-on-read is kept, but *over a DuckDB table materialized from S3 on
> load* (not raw JSON re-reads). So it's **materialized load + compute-on-read queries** — fresh, and it
> scales 30→millions without a rewrite (the "precompute to S3" seam becomes "Parquet-on-S3 + DuckDB httpfs").

## 6. ⟐ DECISION C — Prompt design

- **Field/enum descriptions are the semantic ground truth — consumed from the schema, never hardcoded.**
  The enum *label* ("infotainment_electronics", "undetermined") is meaningless alone; the *description* is
  what maps shorthand → the right value. Two carriers, both sourced at runtime via `schema_loader`:
  (a) `extraction_schema.json` `description` fields ride *into* the `response_format = json_schema`
  constraint automatically; (b) `schema_spec.yaml` `semantic_descriptions` for the calibration-sensitive
  enums (warranty 4-state, severity ordinal) are injected into the prompt as explicit definitions.
  Descriptions are authored **once** in the schema and consumed by **both** the constraint and the prompt —
  this is what enforces `in-warranty ≠ covered` and resolves subsystem shorthand (locked #5).
- **System prompt** = role + the **uncertainty contract** verbatim from `schema_spec.yaml`
  (unsupported → `undetermined`/`unclear`/`null`, never guessed) + the passthrough rule (don't re-extract
  note_id/date/model/year/mileage).
- **Structural conformance via structured outputs.** Request `response_format` = json_schema with the
  loaded schema. Because `openrouter/free` routes to varying models with uneven schema adherence, we
  **also validate defensively** on return (jsonschema) — belt and suspenders. A malformed response is a
  validation fail → retry ≤1 → needs_review.
- **Few-shot severity anchors** (2–3, curated, in-prompt): normal-operation NFF (RO-100024) = `low`;
  infotainment reboot, driveable (RO-100006) = `medium`; backup-camera fails while reversing
  (RO-100026) = `high`/safety_related. Anchors calibrate the ordinal without labels.
- **`evidence_quote` must be a verbatim substring** of the note → deterministic post-check; failure
  downgrades confidence / routes to review. This is the anti-hallucination tripwire.
- **Anchors ≠ `evidence_quote`** (they're orthogonal): anchors are *input* — other notes that calibrate the
  severity scale; `evidence_quote` is *output* — a span from *this* note that grounds the extraction. The
  quote never cites an anchor. We ground on deterministically-checkable source text, not on the model's
  self-explanation of which example it matched.
- Cost note: few-shot inflates *tokens*, not *requests*; the 50/day limit is request-count, so this is free.

## 7. ⟐ DECISION D — Dashboard & review-queue UX

- **Landing = aggregate view.** Table/heat of **subsystem × model × model_year**, sorted by a transparent
  **priority score** so the CR-V infotainment cluster surfaces top-of-page. **Default is severity-dominant**
  (ratified): peak severity leads, so a single `critical`/`high` can outrank a larger `low`/`medium`
  cluster; `note_count` and `recency` are secondary; `safety_related`/`repeat_visit`/`fleet_signal` are
  boosts. Exact weights tuned at build — the decision is that *severity leads*.
  > **Refined by Decision E:** the landing view is the first **curated preset** (a saved query object), and
  > the priority score is a **tunable Measure** — see E for the visible/tunable/reset requirement.
- **Drill-down:** click a cell → note list → note detail with `evidence_quote` highlighted,
  `warranty_status` + `denial_reason`, resolution, and the flag chips (incl. `intermittent`).
- **Review queue tab:** `confidence=low` or validation-failed rows, **excluded from aggregates by
  default** (per uncertainty contract) with a toggle to include.
- **Filters:** model, model_year, subsystem, severity, and flag facets — `intermittent + nff + repeat`
  is the "watch cohort" slice (the leading-edge-of-a-defect view the v0.2.0 flag exists to enable).

## 7.1 ⟐ DECISION E — Aggregation as one grammar (ratified, Session 2)

Supersedes the old "menu of aggregations." Every analytic view — presets, ad-hoc queries, population
stats — is the **same move**: a deterministic pivot expressed as one serializable **query object**.

**The grammar — assign each schema field a role:**
- **Group** — dimensions to pivot on (`subsystem`, `model`, `model_year`, `denial_reason`, …)
- **Filter** — slice: equality / range / boolean over any field (`model_year` range, `warranty_status`, flags)
- **Measure** — what to compute: `count`, severity index, warranty-mix, recurrence rate, **priority score**
- **rank + top_k** — optional; `top_k` is *per group level* → nested top-N

```json
{ "group_by": ["model","subsystem"],
  "filters": { "model_year": [2020,2023], "warranty_status": ["covered"], "flags": {"repeat_visit": true} },
  "measure": { "signal": "recurrence", "agg": "count" },
  "rank": { "by": "measure", "dir": "desc" },
  "top_k": { "model": 10, "subsystem": 3 } }
```

**Executor = DuckDB, in-process (no new container).** The query object is a *logical plan*; a compiler
translates it to **parameterized SQL** — `group_by`→GROUP BY, `filters`→WHERE (bound params),
`measure`→agg, `top_k`→window fn + `QUALIFY` (nested top-k is cleaner in SQL than in pandas). **Field
names are validated against the schema's allowed dimensions (whitelist) before templating** — the grammar
is a safe DSL, not string interpolation; values bind as parameters. (Chose DuckDB-from-start over pandas so
30→1000→millions is the *same code*; pandas would cap in-memory and need a rewrite.)

**S3 = truth, DuckDB = derived view.** On startup/refresh, load all `extractions/*.json` → a flat typed
DuckDB table (unnest `severity_flags`→boolean cols; `meta.*` as cols; `WHERE schema_version = current`).
Restart rebuilds from S3 with **zero LLM calls**. Far-scale seam: write extractions as **Parquet on S3**
and point DuckDB `httpfs` at `s3://…` — same SQL, no full in-memory load.

**Three surfaces over the one engine — all emit the same query object:**
1. **Curated presets** — headline defect board + warranty/watch lenses, run on load → analyst **cold-start**.
   A preset *is* a saved query object (not a separate feature).
2. **Query panel** — Group/Filter/Measure pickers + top-k → ranked answer (the "top-10 models × top-3
   subsystems, recurrent, on-warranty, MY2020–23" case).
3. **Visuals** — output type auto-selected by *(# Group fields, is there a rank/top_k)*: **0 Group** → KPI
   cards; **1–2 Group, no rank** → heatmap / bars; **any rank/top_k** → ranked (nested) **table**.
   Renderer: **Nivo** (native heatmap + bar + treemap) for charts; **HTML/CSS** for the ranked table (the
   workhorse — never mis-renders). A thin `renderResult(result, shape)` picks by the rule; not a general
   charting engine.

**Endpoint:** one `POST /aggregate` takes a query object, returns a tidy result — compute-on-read, **zero LLM**.

**Tunable priority score** (refines Decision D): the score is a Measure carrying a weight vector. **Default
is severity-dominant** (a single `critical`/`high` can outrank a larger `low`/`medium` cluster; count +
recency secondary; safety/repeat/fleet boosts). **The full weight configuration is visible to the analyst,
tunable, and resettable to default — this is core, not stretch** (Sunit, Session 2): an editable weights
panel exposing every factor + a Reset button, not just a read-only tooltip. Weights live in the query
object (shareable). Tuning changes the *ranking lens, not the counts* — the one place we impose judgment,
made fully transparent and overridable. Named presets (safety-/recency-/volume-first) are a convenience on
top.

**LLM boundary & MCP:** the LLM is used **only at ingest** (note → record). All three surfaces are
deterministic and **LLM-free**. **No MCP in core** — there's no agent/tool-calling loop; React calls a
plain REST `/aggregate`. MCP's only natural home is the Phase-3 NL/RAG stretch (expose `/aggregate` as a
tool so an LLM can turn English → query call). Deliberate non-use: no NL→query LLM — a structured panel
instead (cheaper, deterministic, defensible).

**Honesty guardrails (carry across all surfaces):** always show `n`; prefer the table when cells are thin;
keep the score transparent.

**Scaling invariant:** *the schema is the axis; records are points on it.* Adding records under a **fixed
schema** is seamless (validate → S3 → next load includes them, all 3 surfaces update). Schema **extension**
is monotonic (optional-only) but bumps `schema_version` → forces re-extraction (budget cost) + `null` new
fields on old records. The 1000-record demo lives entirely on the cheap (fixed-schema) side.

## 7.2 ⟐ DECISION F — Provider ladder + `LLM_PROVIDER` seam (ratified, Session 2)

**One seam, one interface.** A single `LLMClient` (`extract(note, schema) → record`) selected by env
`LLM_PROVIDER`, with adapters:
- **openai_compat** (`base_url`/`model`/`key`) → covers **OpenRouter** *and* **vLLM** (both OpenAI-API-shaped)
- **bedrock** (boto3 `converse`) → **Claude on AWS** (managed, closed-weight — *not* vLLM, no serving code)

**The ladder (demo + scale story):**
| Phase | Provider | Use | Notes |
|---|---|---|---|
| 1 | **OpenRouter** `openrouter/free` | build + core demo, 30 records | openai_compat adapter; 20/min·50/day budget guard |
| 2 | **Bedrock + Claude** | 1000-record scaling run | bedrock adapter; **REAL AWS** (not LocalStack) → S3 stays emulated = clean hybrid; own key lifts the 50/day cap; ~single-$ cost; `meta.model` keeps the two sets traceable |
| 3 | **Llama + vLLM** | RAG / NL ask-layer | self-hosted, openai_compat; **STRETCH**, gated on core+tests; the *only* path where we write serving code |

Provider budgets/models **never mix** (extends locked #10). The escalation — managed-free → managed-AWS →
self-hosted — is entirely config-only behind the one seam (Bedrock aside, which needs its adapter).

## 7.3 ⟐ DECISION G — Async ingest & live-progress pipeline (ratified, Session 2)

**Principle:** decouple the slow, rate-limited, LLM-bound **ingest** path from the fast, deterministic
**serving** path. The analyst keeps querying while records stream in; reads (DuckDB/S3) and writes (new
extractions) never block each other → **zero downtime during ingest.**

```
Analyst UI ─poll─ GET /jobs/{id}      queued / structuring / done / failed   (%bar)
     │ POST /aggregate ── reads the CURRENT DuckDB view, live throughout
     ▼
POST /ingest(batch) ─▶ 202 + job_id, write jobs/{id}.json manifest to S3
   SQS queue ─▶ worker(s)   (rate-limited, idempotent)
        per msg: S3 cache-check ─hit─▶ skip (0 budget)
                              ─miss▶ extract ─▶ validate
                                 ok  ─▶ write extractions/{id}.json (S3 truth)
                                     ─▶ INSERT into DuckDB view ─▶ job.done++
                                 fail ─▶ retry≤1 ─▶ needs_review + DLQ ; job.failed++
```

**Ratified picks:**
- **Queue = SQS** (LocalStack-emulated — the brief's welcomed 2nd AWS service). Workers sit behind the same
  `extract()` interface, so a lean **in-process asyncio worker is the drop-in fallback** if time is short;
  swapping up to SQS + Lambda changes no core logic.
- **Job status = S3 `jobs/{id}.json` + counters** (total / done / failed / needs_review). DynamoDB (atomic
  counters, per-record rows) is the noted scale-up.
- **Progress = polling** `GET /jobs/{id}` (~1 s). SSE/WebSocket = UX upgrade note.
- **Analytics refresh = poll-while-active:** the UI re-queries `/aggregate` while the job runs → the board
  re-ranks live and settles on completion. The **batch-health strip (surface #6) becomes the live progress
  surface** during ingest, then reverts to the trust indicator.

**Safety properties:**
- **Idempotent under SQS at-least-once:** the S3 cache-check dedups, so redeliveries/retries never
  double-spend budget.
- **Rate honored:** worker concurrency + `budget.py` throttle + daily ledger, per provider (Phase-2 Bedrock
  just raises the cap).
- **Failures quarantined:** needs_review in S3 + SQS **DLQ**; excluded from the 3 surfaces by default.

**Prototype ↔ real AWS:**
| Concern | Prototype (compose + LocalStack) | Real AWS |
|---|---|---|
| Ingest API | FastAPI `POST /ingest` → 202 + job_id | API Gateway + FastAPI on ECS Fargate |
| Queue | SQS (LocalStack) | SQS + DLQ |
| Workers | asyncio worker, semaphore-throttled | Lambda (SQS-triggered) / ECS; reserved concurrency = rate cap |
| Truth | S3 `extractions/{id}.json` | S3 |
| Query view | DuckDB in-process, incremental INSERT | DuckDB/Parquet-on-S3 / Athena |
| Job status | S3 `jobs/{id}.json` + counters | DynamoDB |
| Progress → UI | poll `GET /jobs/{id}` | poll / API GW WebSocket / AppSync |
| Failures | needs_review + SQS DLQ | DLQ + CloudWatch alarm |

Largest add beyond the core loop — but it's the **1000-record live-demo centerpiece**; the in-process
fallback keeps it safe under the 8–12h budget.

## 8. Env contract (`.env.example`)

| Var | Purpose | Example |
|-----|---------|---------|
| `LLM_PROVIDER` | provider seam (Decision F) | `openrouter` \| `bedrock` \| `vllm` |
| `OPENROUTER_API_KEY` | extraction LLM auth (openai_compat) | `sk-or-…` |
| `OPENROUTER_BASE_URL` | OpenAI SDK base | `https://openrouter.ai/api/v1` |
| `LLM_MODEL` | extraction model | `openrouter/free` |
| `BEDROCK_MODEL_ID` | *(phase 2)* Claude on Bedrock | `anthropic.claude-…` |
| `DISCOVERY_LLM_BASE_URL` | *(optional)* local discovery LLM | `http://localhost:11434/v1` |
| `DISCOVERY_LLM_MODEL` | *(optional)* discovery model | `llama3.2:3b` |
| `AWS_ENDPOINT_URL` | LocalStack S3 | `http://localstack:4566` |
| `S3_BUCKET` | cache bucket | `repair-triage` |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | dummy for LocalStack | `test` / `test` |
| `AWS_REGION` | region | `us-east-1` |
| `SCHEMA_PATH` | active schema (schema-driven swap) | `schema/extraction_schema.json` |
| `MAX_REQUESTS_PER_MIN` | throttle | `20` |
| `MAX_REQUESTS_PER_DAY` | daily budget gate | `50` |
| `RETRY_CAP` | per-note retries before needs_review | `1` |
| `INGEST_QUEUE_URL` | *(Decision G)* SQS ingest queue | `http://localstack:4566/000000000000/ingest` |
| `WORKER_CONCURRENCY` | *(Decision G)* parallel extract workers | `4` |

Extraction (`OPENROUTER_*`) and discovery (`DISCOVERY_LLM_*`) budgets/models **never mix** (locked #10).
`config.py` fails fast if a required var is missing so the clean-clone run errors loudly, not silently.

## 9. API surface

| Method · Path | Purpose |
|---|---|
| `POST /extract/run` | synchronous core-loop batch-extract of the CSV, cache-first; returns `{processed, from_cache, needs_review, budget_used, budget_remaining}` |
| `POST /ingest` | **Decision G** — accept a batch (CSV/records), enqueue to SQS, write job manifest; returns `202 {job_id}` (async path for adding records live) |
| `GET /jobs/{job_id}` | **Decision G** — job progress: `{total, queued, structuring, done, failed, needs_review}` — drives the progress bar |
| `POST /aggregate` | **Decision E** — takes a query object (Group/Filter/Measure/rank/top_k), returns a tidy result; compute-on-read over DuckDB, zero LLM. Presets, query panel, and visuals all hit this one endpoint |
| `GET /presets` | curated query objects for cold-start (headline board, warranty lens, watch cohort) |
| `GET /extractions` | list records (filters: model, subsystem, severity, flag, needs_review) |
| `GET /extractions/{note_id}` | single record + evidence |
| `GET /review-queue` | needs_review / low-confidence rows |
| `GET /schema` | active schema + version (transparency) |
| `GET /budget` | remaining daily calls (read from S3 ledger) |
| `GET /health` | liveness |

## 10. Build order (~2 days)

**Day 1 — core loop (prove it end-to-end on real budget once):**
1. `backend/config.py` + `store_s3.py`; LocalStack bucket bootstrap (compose init).
2. `schema_loader.py` + wire `schema_tools --validate` as a start gate.
3. `budget.py` (min throttle + daily S3 ledger) → `llm_client.py` → `extract.py` (cache→LLM→validate→write).
4. `POST /extract/run` over the 30 notes **once**; verify: re-run = 0 LLM calls; needs_review path works.

**Day 2 — surface + ship:**
5. `aggregate.py` + priority score + `GET /aggregate/subsystem`.
6. Frontend: aggregate → drill-down → review queue; confirm the CR-V cluster lands on top.

**Ingest pipeline (Decision G — enables the 1000-record live demo; the largest optional add):**
- `ingest.py` (`POST /ingest` → SQS enqueue + S3 job manifest) + `worker.py` (consume → `extract()` → DuckDB
  INSERT → job status) + `GET /jobs/{id}` + frontend progress bar with poll-while-active `/aggregate` refresh.
- **Fallback if time-short:** ship the in-process asyncio worker only (same `extract()` interface, no SQS) —
  live progress still works; SQS is the swap-up for the cloud story.

7. `docker-compose.yml` (frontend/backend/localstack) + `.env.example` + bucket-init.
8. `README.md` (assumptions, architecture, setup, shortcuts, scaling, real-AWS) + `LLM-USAGE.md`; append `docs/` logs.
9. **Clean-clone test** (reserved, hard gate): fresh checkout + evaluator's own key runs exactly as README says.

## 11. Testing / determinism

- **No-LLM tests** for `schema_tools`, structural validation, `evidence_quote` substring check, and
  `aggregate.py` (fixture of cached extraction JSONs → asserts the CR-V cluster ranks #1). CI never spends budget.
- **Optional `SEED_FIXTURES` mode:** pre-seed S3 from a committed fixture of 30 extraction records so the
  dashboard is demonstrable without any LLM calls. The *primary* clean-clone path still calls the LLM with the
  evaluator's key (per the brief); fixtures are a reviewer convenience, clearly labeled.

## 12. Real-AWS mapping (README section — from deploy-notes)

LocalStack S3 → S3 (drop `AWS_ENDPOINT_URL`, identical boto3); backend container → ECS Fargate (or Lambda for
batch extraction); the **Decision G SQS ingest queue** decouples ingest from rate-limited extraction (SQS-
triggered Lambda workers + DLQ at scale; job status → DynamoDB); `.env` → Secrets Manager / SSM; CloudWatch
metrics on validation-failure rate by model/subsystem. AgentCore is the natural reference point in the
deployment-plan narrative without over-building the prototype.

## 13. Open items for Sunit

- **Decisions E–F: RATIFIED** (Session 2). **A: accept** (S3 layout + provenance stamp). **B, D: refined
  by E** (DuckDB materialized-load + compute-on-read; landing = first preset; score = tunable Measure).
- **C (prompt design): RATIFIED** (Session 2) — as written in §6 (schema-descriptions-as-ground-truth, uncertainty contract, few-shot anchors, `evidence_quote` tripwire).
- **Decision G — async ingest / live-progress pipeline: RATIFIED** (Session 2). SQS + in-process worker
  (SQS-swappable) · S3 job manifest · polling · poll-while-active refresh. See §7.3.
- `intermittent` required-vs-optional at baseline (currently required; see build-notes Jul 14).
- Priority-score **default weights: RATIFIED severity-dominant** (Session 2) — a single `critical`/`high`
  can outrank a larger cluster; count+recency secondary; safety/repeat/fleet boosts. Full config **visible +
  tunable + reset-to-default** in the UI (core, per §7.1).
- Frontend: **RATIFIED plain React (Vite) + Nivo + CSS tables** (Session 2). Streamlit rejected — the brief
  pins Next/React + separate frontend/backend containers; Streamlit fails both. Next.js adds SSR we don't need.

**All decisions A–G are now ratified. Architecture is closed — ready for the build phase.**
