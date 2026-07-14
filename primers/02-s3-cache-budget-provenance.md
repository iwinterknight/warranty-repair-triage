# Primer: S3 cache, budget & provenance   ·   ~6 min   ·   [Cloud · Exec]
> Why S3 is *load-bearing*: it's the cache that makes restarts free, the ledger that enforces the daily
> budget, and the audit trail that makes every record traceable.

## The concept (first principles)
The free tier (50 calls/day) makes **cache-first mandatory**, not optional. So S3 isn't just storage — it's
the thing that lets a re-run cost **zero** LLM calls:
- **Cache key = `schema_version` + `note_sha256`.** Same schema + same note text → reuse. A schema bump or
  an edited note changes the key → transparent re-extraction. Nothing else forces a re-call.
- **Provenance `meta`** on every record (`model`, `prompt_version`, `git_sha`, …) → any output traces back
  to the exact code, schema, and prompt that produced it. *Deliberately excluded from the cache key* — a
  rebuild at the same schema+prompt must not bust the cache.
- **Daily ledger** in S3 (`_budget/{day}.json`) survives restarts, so the 50/day cap is real across runs.

## In the code
- `backend/store_s3.py` → `get_extraction()` / `put_extraction()` / `list_extractions()` — the cache repo
  (path-style boto3 → LocalStack now, real S3 by dropping the endpoint). `list_extractions()` is what the
  DuckDB view will materialize from.
- `backend/store_s3.py` → `get_budget_used()` / `incr_budget()` — the durable daily ledger.
- `backend/extract.py` → `_is_cache_hit()` — the schema_version + note_sha256 check (provenance excluded).
- `backend/extract.py` → the `meta` block in `extract_note()` — the provenance stamp written per record.
- `backend/budget.py` → `check_daily()` (gate before a call) + `throttle()` (per-minute sliding window).

## Why it's built this way
→ ADR-0002 (S3 layout + provenance) · locked #2 (S3 = load-bearing cache) · #4 (budget). Restart-safety
and auditability both fall out of the same design.

## Probe deeper? (pick your dive)
- 🔍 **Why provenance is excluded from the cache key** — the subtle bug it avoids (a rebuild needlessly
  re-spending the whole budget) — `_is_cache_hit()` + the `meta` block.
- 🔍 **The persistence rule in `extract_note()`** — why *transient* failures (budget/network, no candidate)
  are **not** cached, but invalid candidates are. Prevents a budget-skipped note from freezing as a false
  cache hit.
- 🔍 **`incr_budget()` is read-modify-write** — fine for the single-writer prototype; the atomic-counter
  (DynamoDB) upgrade at scale, and why it matters once workers run concurrently (Decision G).
