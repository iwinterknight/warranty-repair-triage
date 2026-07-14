# Final Project Doc — outline & talking-point bank

Seed for the **single polished, interview-specific project doc** assembled AFTER the build (see task #6).
Not shipped as-is; the raw `docs/*-notes.md` logs stay as-is. Each section is tagged with the assignment
**evaluation axis** it serves: `[Exec] [Judgment] [AI-depth] [Cloud] [Comm]`.

## Planned sections
1. Problem framing & the two cruxes (schema-under-ambiguity; value-is-in-aggregation) `[Judgment][Comm]`
2. Architecture & key decisions (the 10 locked decisions, each as a why) `[Exec][AI-depth]`
3. Schema design story: EDA → validation → v0.2.0, generalization seams `[AI-depth][Judgment]`
4. LLM approach: schema-driven extraction, uncertainty contract, budget-as-forcing-function `[AI-depth]`
5. Cloud story: env-driven config, S3-as-cache/audit, LocalStack→AWS mapping `[Cloud]`
6. **Documentation strategy & judgment** (topic A below) `[Comm][Judgment]`
7. **Provenance: aligning design, code, and LLM-use in Git** (topic B below) `[AI-depth][Cloud][Comm]`
8. **How LLM-USAGE.md was constructed** (below) `[Comm]`
9. Shortcuts taken & what I'd do next (honest tradeoffs under the 8–12h budget) `[Judgment][Comm]`

---

## Topic A — Documentation beyond the README (the judgment being graded) `[Comm][Judgment]`

**Thesis:** the brief grades *doc judgment*, not doc volume. My rule: **documentation lives at the altitude
of what it describes and is discoverable from there.** More docs isn't the goal; deliberate placement is.

**Doc set, by reader × change-rate:**
| Doc | Reader | Why here |
|-----|--------|----------|
| `README.md` (hub) | evaluator running a clean clone | front door: what/why, quickstart, arch-at-a-glance, links *down* |
| `docs/decisions/` (ADRs) | engineer asking "why this?" | immutable, numbered records of consequential choices; superseded not deleted |
| `docs/sdd.md` | engineer extending it | the "how" — living during build |
| `docs/*-notes.md` | me / process transparency | raw chronological journal |
| `schema/schema_spec.yaml` + `schema/README.md` | anyone touching the contract | self-documenting; the runtime *also consumes* `semantic_descriptions` |
| module `README.md`s (backend/frontend/eda/schema_tools) | contributor in that dir | run/test/extend next to the code |
| OpenAPI `/docs` (FastAPI) | API consumer | auto-generated from Pydantic — can't drift |
| `.env.example` | operator | the env contract as documentation |
| `LLM-USAGE.md` | evaluator (AI transparency) | required disclosure |

**Judgment moves to call out in the interview:**
- **README as hub, not dump** — deeper docs live closer to their subject.
- **Prefer docs that can't drift** — OpenAPI from code, schema descriptions consumed at runtime, tests-as-docs, `.env.example`.
- **Decided what NOT to ship** — raw AI session logs are transparency, not polish; synthesized into ADRs + this doc, kept the raw logs clearly labeled. Restraint is judgment too, and the brief explicitly de-scopes polish.
- **Made the strategy legible** — this `docs/README.md`/index states who each doc is for and why it's there, so the judgment is visible, not implied.
- **Proportionality** — sized to an 8–12h prototype: ADRs are ~15 lines each, not a wiki.

### A.1 — Self-composing documentation (the load-bearing bit) `[Comm][AI-depth]`
The docs are modular *and* recomposable. `docs/README.md` is both the **human-readable doc map** and a
**load-bearing LLM compose instruction** + manifest: point any LLM at the `docs/` folder and it assembles
the modular parts into one coherent human-readable narrative, following the compose recipe in the file
itself (read manifest → read in `compose-order` → synthesize named sections → rules: ADRs=why, SDD=how,
notes=chronology, most-recent-ratified wins, never invent). A reader can inject **focus directives**
("expand the aggregation design; enumerate the AWS parts; skip the process logs") and get a tailored
narrative. Why this is judgment, not gimmick:
- The instruction to build the human-readable whole **lives inside the documentation** → the full picture is
  *regenerable*, never hand-maintained in parallel with the parts (no drift between "the docs" and "the doc").
- It's the documentation analog of infra-as-code: **narrative-as-code**. The modular docs are the source;
  the composed doc is a build artifact.
- Recorded as [ADR-0001](decisions/0001-adopt-adrs-and-self-composing-docs.md); the map is `docs/README.md`.
- Talking point: *this very project doc can be (re)composed by the mechanism, then polished by hand.*

## Topic B — Aligning SDD + code-build + LLM-use histories in Git `[AI-depth][Cloud][Comm]`

**Thesis:** at any commit you can reconstruct *what the design said, what the code did, and how the LLM
was involved* — one auditable chain, not three disconnected stories. This is a provenance/reproducibility
argument, which is catnip for an ML-platform (AgentCore) role.

**What I actually did (cheap, in-scope):**
1. **Co-commit** — a decision's ADR/SDD edit, its code, and the `LLM-USAGE.md` update land in the same commit/PR, so the diff shows all three move together.
2. **Commit trailers** make `git log` the joined timeline:
   ```
   feat(extract): schema-constrained OpenRouter call + defensive validation
   Design: docs/decisions/0004-schema-driven-pipeline.md
   Schema: v0.2.0
   LLM-Assisted: drafted extractor scaffold; human-reviewed
   Co-Authored-By: Claude <noreply@anthropic.com>
   ```
   `git log --grep` reconstructs any of the three histories.
3. **Provenance stamping** bridges git ↔ runtime: each S3 extraction record's `meta` carries `git_sha` +
   `schema_version` + `prompt_version` (hash of the versioned prompt template). Any output traces to the
   exact code commit, schema version, and prompt that produced it. Prompts are versioned in-repo, so
   `git blame` ties extraction behavior to a commit.
4. **Aligned versions** — `schema-v0.2.0` is stamped in the artifact, in the record `meta`, and as a git tag; one version, consistent across all three.

**What I'd add at scale (explicitly out of scope now):** a machine-readable dev-LLM-call log, PR-per-ADR
gates, CI that fails on schema/record version drift. Noted as "what I'd do next," not built.

## How LLM-USAGE.md was constructed `[Comm]`

**Guidelines adhered to:**
- **Scope = exactly the brief's three bullets** — (1) which tools, (2) what for, (3) what AI-generated I
  changed significantly & why. Nothing else. I deliberately moved runtime/product LLM usage OUT (that
  belongs in README/architecture) — matching the brief's intent that this file is *dev-time disclosure*.
- **Brief & honest, first-person** — the brief says "not a test of how little AI you used." Listed only
  tools actually used (Claude Code); left a marker to add others only if truly used — no padding.
- **Led with the integrity signal** the follow-up interview probes for — concrete AI output I *changed*
  and why (overfit `repeat_visit` regex → split out `intermittent`; always-true empty-match regex;
  rejected zero-shot-NLI/NER for OOD shorthand). Demonstrates "understood, didn't just accept."
- **Concise / human-readable / ratifiable** (standing preference) — short bullets; a pre-submission
  checklist kept as an HTML comment so it won't render in the shipped file.
- **Derived, kept in sync** — regenerated from CLAUDE.md + `docs/`, updated in the same commits as the
  features it describes (topic B), finalized at build with real specifics.
