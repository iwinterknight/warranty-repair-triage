# Primer: Aggregation grammar → DuckDB   ·   ~8 min   ·   [AI depth · Exec]
> One grammar answers *every* analytic question — presets, ad-hoc slices, population stats — by compiling a
> query object into parameterized DuckDB SQL. This is the technical-depth centerpiece.

## The concept (first principles)
Instead of hardcoding rollups, we treat a query as a **logical plan** and compile it to SQL:
- Assign each field a **role** — **Group** (pivot on), **Filter** (slice), **Measure** (compute) — plus
  optional **rank** + **top_k**.
- A tiny compiler turns that object into SQL: `group_by`→GROUP BY, `filters`→WHERE, `measure`→agg,
  nested `top_k`→window + `QUALIFY`.
- **DuckDB from the start** so the *same code* runs 30 → 1000 → millions (pandas would cap in-memory).
- **S3 = truth, DuckDB = derived view** — rebuilt from cached records on load.

Safety matters here: field names are checked against a **whitelist** (`_DIMENSIONS`) before being templated;
values **bind as parameters**; numeric weights are coerced to float. So the grammar is a *safe DSL*, not
string interpolation — no SQL injection surface.

*Toy example* — "top-10 models × top-3 subsystems" compiles to a CTE + two `QUALIFY row_number()` windows
(a matrix can't sort-and-nest; a table can).

## In the code
- `backend/query_engine.py` → `flatten()` — one cached record → one flat typed row (unnest `severity_flags`).
- `backend/query_engine.py` → `compile_query()` — **the translator**: the whole grammar → SQL. Read this one.
- `backend/query_engine.py` → `_where()` — the whitelist + parameter binding (the injection guard).
- `backend/query_engine.py` → `QueryEngine.build_from_records()` / `run()` — materialize view, execute.
- `backend/presets.py` → `PRESETS` — three saved query objects (a preset *is* a query object).
- `tests/test_aggregate.py` — seeds fixtures, asserts the CR-V cluster ranks #1 (verified ✓).

## Why it's built this way
→ ADR-0006 (aggregation-as-one-grammar, DuckDB) · SDD §7.1. Three UI surfaces (presets, query panel,
visuals) all emit this one object and hit one `/aggregate` — no divergent code paths, zero LLM in analytics.

## Probe deeper? (pick your dive)
- 🔍 **`compile_query()` — the nested top-k branch** — how `len(group_by)==2 + top_k` becomes the CTE +
  `QUALIFY` pattern, and why DuckDB windows beat pandas here.
- 🔍 **The whitelist guard in `_where()`** — how `_DIMENSIONS`/`_RANGE_COLS` + bound params make arbitrary
  analyst queries safe.
- 🔍 **`S3 = truth, DuckDB = derived`** — `build_from_records()` + the far-scale seam (Parquet-on-S3 + httpfs).
