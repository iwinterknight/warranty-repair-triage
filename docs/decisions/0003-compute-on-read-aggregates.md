# ADR-0003: Compute-on-read aggregates (Decision B)
- Status: Accepted — 2026-07-14 · **refined by [ADR-0006](0006-aggregation-grammar-duckdb.md)**
- Deciders: Sunit, Claude
- Related: SDD §5, §7.1

## Context
Aggregates must always be fresh with no invalidation burden at prototype scale (30 records).

## Decision
Compute aggregates **on read** rather than precomputing to S3. Refined by ADR-0006: reads run over a
**DuckDB table materialized from S3 on load** (not raw JSON re-reads) — i.e. *materialized load +
compute-on-read queries*. The "precompute to S3" idea becomes the far-scale seam (Parquet-on-S3 + DuckDB
httpfs).

## Alternatives
- **Precompute now** — adds a staleness/invalidation problem for no prototype benefit. Rejected.

## Consequences
- + Always fresh, zero staleness surface.
- + Scales 30→millions without a rewrite (see ADR-0006).
