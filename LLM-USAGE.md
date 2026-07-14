# LLM-USAGE.md

AI coding tools were used to build this project. This is a brief, honest disclosure of which tools, what
for, and what I changed. (Draft — finalized at submission.)

## Tools used
- **Claude Code (Claude Opus)** — primary assistant, used as researcher/engineer under my direction.
<!-- add any others actually used, e.g. ChatGPT / Cursor / Copilot — do not list tools you didn't use -->

## What I used them for
- **EDA & schema:** the corpus-analysis notebook and the extraction schema, authored from the notebook's
  evidence (not free-styled).
- **Design docs:** the SDD, decision records, and the running `docs/` logs.
- **Code, Docker, prompts:** backend/frontend scaffolding, `docker-compose` + LocalStack config, and the
  extraction prompt design. *(filled in as the build proceeds)*
- **Debugging:** tracing validation failures and edge cases.

## What I changed significantly, and why
I reviewed AI output rather than accepting it; the notable corrections (logged in `docs/build-notes.md`):
- **Overfit heuristic** — an AI-written `repeat_visit` regex was fitted to a single note and conflated
  *intermittent fault behavior* with *service history*. I generalized it and split the two signals — which
  is what led me to add `intermittent` as its own schema flag.
- **Always-true regex** — an abbreviation-mining cell used a pattern that always matched the empty string,
  silently emptying the downstream token mining. I replaced it with an explicit exclusion.
- **Rejected an approach** — an initial zero-shot-NLI / generic-NER design was wrong for this data
  (out-of-domain repair shorthand, uncalibrated scores); I replaced it with the MiniLM +
  `semantic_descriptions` design.
- *(more added as the build proceeds)*

---
<!-- Open items — remove before submission:
     [ ] add any other AI tools actually used
     [ ] fill in code / Docker / prompt specifics after the build
     [ ] final honesty + brevity pass -->
