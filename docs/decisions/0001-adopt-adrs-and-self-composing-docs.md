# ADR-0001: Adopt ADRs + self-composing modular documentation
- Status: Accepted — 2026-07-14 (Session 2)
- Deciders: Sunit (architect), Claude (researcher/engineer)
- Related: SDD §2, [`../README.md`](../README.md) (the documentation map + compose instruction)

## Context
The brief grades *"documentation beyond the README"* and *"judgment under ambiguity."* The project has
many docs at different altitudes (contract, decisions, design, process, disclosure). Two needs: (a) a
durable **decision trail**, and (b) a way to turn the modular docs into a single **human-readable** picture
on demand — the parts alone don't read as one narrative.

## Decision
1. Record consequential decisions as **immutable numbered ADRs** in `docs/decisions/`; SDD = the "how",
   CLAUDE.md = the terse locked index.
2. Make the documentation **self-composing**: `docs/README.md` is both a human-readable **doc map** and a
   **load-bearing LLM compose instruction** + manifest. Pointing any LLM at `docs/` regenerates the full
   human-readable narrative, and a user can inject focus directives ("expand the aggregation design;
   enumerate the AWS parts").

## Alternatives
- **Single top-level README dump** — loses the decision trail and can't be recomposed with focus.
- **Off-repo wiki** — drifts from code; not versioned with the change.

## Consequences
- + Hits two grading axes directly; docs are modular *and* recomposable.
- + The full picture is regenerable, not hand-maintained in parallel with the parts.
- − Requires discipline: keep ADRs immutable and the `docs/README.md` manifest current.
