# Feature Build Primers

Short, concept-first walkthroughs of the **core** features, written as each is built. Separate from `docs/`
on purpose: these are a **fast-read learning aid** (and interview prep) — not the shipped project docs.

## How to use these
1. Read the **one-liner + "The concept"** of each (a couple minutes each).
2. Only where you want deeper eyes on the logic, follow the **"Probe deeper?"** hooks — they name the exact
   spots worth diving into. You decide the depth; the primer gets you oriented first.
3. Total Tier-1 read ≈ **40 minutes**. Sized so you can get through it all in a day and still probe.

## Primer template
```
# Primer: <feature>   ·   ~<n> min   ·   [eval axis]
> One line: what it is and why it matters for the assignment.

## The concept (first principles)
Plain language + a toy example. The fundamental being implemented — no code yet.

## In the code
- `backend/<file>.py` → `<function>()` — what it does, the fundamental it implements.
  (line refs are clickable but anchored on function names, since lines shift.)

## Why it's built this way
Link to the decision: → ADR-000X / SDD §X.

## Probe deeper? (pick your dive)
- 🔍 <spot 1 worth a closer look — and what you'll learn there>
- 🔍 <spot 2>
```
*Discipline: concept before code; ~1 page; if it needs more, the depth goes behind a "Probe deeper" hook,
not inline.*

## Planned primers — tiered by assignment relevance

**Tier 1 — must-read (the parts evaluators look at).** Written as each feature lands.

| # | Primer | Eval axis | ~min |
|---|---|---|---|
| 1 | **Schema-driven extraction** — the LLM call: schema-as-constraint + structured output + defensive validation + `evidence_quote` tripwire + uncertainty contract | AI depth | 8 |
| 2 | **S3 cache, budget & provenance** — cache-first (restart = 0 calls), daily ledger, `meta` provenance stamp | Cloud · Exec | 6 |
| 3 | **Aggregation grammar → DuckDB** — query object → parameterized SQL, schema-whitelist safety, the 3 surfaces over one engine | AI depth · Exec | 8 |
| 4 | **Priority score** — severity-dominant default, transparent + tunable + reset (the one imposed judgment) | Judgment | 5 |
| 5 | **Async ingest / live-progress** — SQS, idempotent workers, job status, poll-while-active; LocalStack→AWS map | Cloud | 7 |
| 6 | **Provider seam** — `LLM_PROVIDER` adapters (OpenRouter→Bedrock→vLLM); env-only portability | Cloud | 5 |

**Tier 2 — optional (skim if curious).** Lighter primers only if time allows.
- Config & fail-fast env contract · `schema_tools` validation gate · frontend render-by-shape (table vs Nivo).

**Tier 3 — no primer (inline code comments suffice).**
- docker-compose wiring, bucket bootstrap, boilerplate routes.

## Selection principle
Primers go to the concepts that (a) carry the assignment's grade (AI depth, cloud reasoning, judgment) and
(b) contain a *non-obvious fundamental* worth understanding. Boilerplate gets comments, not a primer.
