# ADR-0005: Aggregate-first dashboard + review queue (Decision D)
- Status: Accepted — 2026-07-14 · refined by [ADR-0006](0006-aggregation-grammar-duckdb.md)
- Deciders: Sunit, Claude
- Related: SDD §7, §7.1

## Context
The analyst's job is to spot emerging defects and triage — not to read notes one by one. Value is in
aggregation, and the planted CR-V infotainment cluster must surface immediately.

## Decision
Landing = **aggregate board** (`subsystem × model × model_year`) ranked by a **priority score** whose
**default is severity-dominant** (a single `critical`/`high` can outrank a larger `low`/`medium` cluster;
count + recency secondary; safety/repeat/fleet boosts). The **full weight config is visible, tunable, and
reset-to-default in the UI** (core). Drill-down → note detail with `evidence_quote` highlighted. A
**needs_review queue** (low-confidence / validation-failed) is excluded from aggregates by default.

## Alternatives
- **Note-list-first** — misses the batch patterns; rejected.
- **Neutral sortable columns only** — defers all judgment; rejected in favor of a transparent, *overridable* opinion.

## Consequences
- + The cluster surfaces on load; uncertainty is a first-class, quarantined output.
- − The score imposes judgment → mitigated by full transparency + tunability + reset.
