# LLM-USAGE.md

AI coding tools were used to build this project. This is a brief, honest disclosure of which tools, what
for, and what I changed.

## Tools used
- **Claude Code (Claude Opus)** — the only AI tool used; driven as a researcher/engineer under my
  direction (I set the architecture; it proposed, implemented, and verified).

## What I used them for
- **EDA & schema:** the corpus-analysis notebook and the extraction schema, authored from the notebook's
  evidence (not free-styled).
- **Design docs:** the SDD, the ADRs, the running `docs/` logs, and the feature primers.
- **Code:** the FastAPI backend (schema-driven extraction pipeline, S3 cache/ledger, DuckDB query engine),
  the React dashboard, and the tests.
- **Prompt design:** the schema-driven extraction prompt (semantic descriptions injected from the schema,
  uncertainty contract, few-shot severity anchors, evidence-quote tripwire).
- **Docker config:** docker-compose (LocalStack + backend + frontend) and both Dockerfiles.
- **Debugging:** live end-to-end verification that caught real bugs (below).

## What was AI-generated that I changed significantly, and why
I reviewed and exercised AI output rather than accepting it; notable corrections (logged in
`docs/build-notes.md`):
- **Overfit heuristic (EDA)** — an AI-written `repeat_visit` regex was fitted to a single note and
  conflated *intermittent fault behavior* with *service history*. I generalized it and split the signals —
  which led to adding `intermittent` as its own schema flag.
- **Always-true regex (EDA)** — an abbreviation-mining pattern matched the empty string, silently emptying
  downstream mining. Replaced with an explicit exclusion.
- **Rejected an approach** — an initial zero-shot-NLI / generic-NER design was wrong for out-of-domain
  repair shorthand (uncalibrated scores); replaced with the schema + semantic-descriptions design.
- **Live-caught pipeline bugs (build)** — running the real stack surfaced two defects in AI-written code
  that fixture tests missed: the aggregation view crashed on a malformed model response
  (`severity_flags` returned as a list), and parallel dashboard requests corrupted results through a
  shared DuckDB connection (fixed with per-engine locking). Both fixes were made and documented after I
  insisted on end-to-end verification with the real model and browser.
- **UX corrections from my review** — the drill-down rendered off-screen (looked broken), the heatmap
  button was dead at the default grouping, and malformed flags rendered as a bogus “0” chip; each was
  found by me exercising the UI and then fixed.

Kept deliberately: the follow-up interview walks this code, and everything shipped here is something I can
explain and defend — the `docs/` decision records and `primers/` walkthroughs exist for exactly that.
