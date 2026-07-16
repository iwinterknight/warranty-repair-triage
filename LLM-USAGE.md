# LLM-USAGE.md

AI coding tools were used to build this project. This is a brief, honest disclosure of which tools, what
for, and what I changed.

## Tools used
- **Claude Code (Claude Opus)** — the only AI tool used, operated as a directed engineer.
  **I owned the architecture and every consequential decision**; the assistant researched options,
  implemented under my direction, and ran verification I demanded. The design calls were mine:
  aggregation-first framing, the 4-state warranty spectrum, the schema-driven pipeline, cache-first S3,
  the severity-dominant (tunable) priority score, the single aggregation grammar, the provider seam, and
  the dashboard UX (group-by granularity, heatmap, contributing-records audit view, live progress).

## How I worked with it — the per-feature loop
Every feature went through the same loop before the next one started:
1. **Spec.** I framed the task and its design constraints (the accepted decisions are recorded as ADRs in
   `docs/decisions/`).
2. **Discussion & clarification.** Before accepting an implementation I probed it — why this structure,
   what are the tradeoffs, what breaks it (e.g. I pushed back on the scoring scheme until it was
   explainable in plain English, questioned the aggregation grammar's SQL-injection surface, and drove
   the heatmap/group-by UX decisions).
3. **Read–verify–modify at code level.** I read the generated code (the `primers/` walkthroughs exist
   because I required line-level explainability), exercised the running app myself, and sent back
   concrete corrections. Nothing was "done" until it survived this pass.

## What I used it for
- **EDA & schema:** the corpus-analysis notebook and the extraction schema, authored from the notebook's
  evidence (not free-styled).
- **Design docs:** the SDD, ADRs, running logs, and feature primers.
- **Code:** the FastAPI backend (schema-driven extraction, S3 cache/ledger, DuckDB query engine), the
  React dashboard, and the tests.
- **Prompt design:** the schema-driven extraction prompt (semantic descriptions injected from the schema,
  uncertainty contract, few-shot severity anchors, evidence-quote tripwire).
- **Docker config:** docker-compose (LocalStack + backend + frontend) and both Dockerfiles.
- **Debugging:** end-to-end verification runs that surfaced real defects (below).

## What was AI-generated that I changed significantly, and why
- **Overfit heuristic (EDA)** — an AI-written `repeat_visit` regex was fitted to a single note and
  conflated *intermittent behavior* with *service history*. I had it generalized and split — which led to
  adding `intermittent` as its own schema flag.
- **Always-true regex (EDA)** — an abbreviation-mining pattern matched the empty string, silently emptying
  downstream mining. I caught it in review; replaced with an explicit exclusion.
- **Rejected an approach** — an initial zero-shot-NLI / generic-NER design was wrong for out-of-domain
  repair shorthand; I redirected to the schema + semantic-descriptions design.
- **Live-caught pipeline bugs** — I insisted features be verified against the real model and browser, not
  just fixture tests; that surfaced a crash on a malformed model response (`severity_flags` as a list) and
  result corruption from a shared DuckDB connection under parallel requests. Both fixed and documented.
- **UX corrections from my own testing** — drill-down rendering off-screen, a dead heatmap toggle at the
  default grouping, bogus "0" flag chips from malformed output, missing mileage surfacing, and the live
  extraction-progress requirement — each found by me exercising the UI, then specified and fixed.

The follow-up interview walks this code: everything shipped survived the loop above, and the
`docs/decisions/` records and `primers/` walkthroughs exist so each choice is defensible line-by-line.
