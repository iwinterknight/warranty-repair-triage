# ADR-0006: Aggregation as one grammar, DuckDB executor (Decision E)
- Status: Accepted — 2026-07-14
- Deciders: Sunit, Claude
- Related: SDD §7.1 · refines [ADR-0003](0003-compute-on-read-aggregates.md), [ADR-0005](0005-aggregate-first-dashboard.md)

## Context
Analysts need population stats, arbitrary *signal × actor* slices, and ranked top-k queries (e.g. "top-10
models × top-3 subsystems, recurrent, on-warranty, MY2020–23") — and it must scale 30 → 1000 → millions.

## Decision
Every view is one serializable **query object**: assign each field a role — **Group / Filter / Measure**
(+ optional `rank`, `top_k`). A compiler translates it to **parameterized DuckDB SQL** (field names
validated against the schema whitelist → safe DSL, not string interpolation). **S3 = truth, DuckDB =
derived view** materialized on load. Three surfaces — **presets, query panel, visuals** — all emit the same
object and hit one `POST /aggregate`. The **LLM is used only at ingest**; analytics are deterministic.
Priority score is a tunable Measure.

## Alternatives
- **pandas executor** — caps in-memory, needs a rewrite to scale. Rejected (DuckDB-from-start).
- **Fixed hardcoded rollups** — not general enough for arbitrary analyst queries.
- **NL→query LLM** — budget/determinism cost; use a structured panel instead.
- **MCP** — no agent/tool-calling loop in core; plain REST. (MCP only fits the Phase-3 NL/RAG stretch.)

## Consequences
- + Same code 30→millions (Parquet-on-S3 + httpfs seam); arbitrary queries for free; zero LLM in analytics.
- − Must guard SQL injection via the schema-derived column whitelist + bound parameters.
