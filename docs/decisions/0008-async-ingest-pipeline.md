# ADR-0008: Async ingest / live-progress pipeline (Decision G)
- Status: Accepted — 2026-07-14
- Deciders: Sunit, Claude
- Related: SDD §7.3, §9, §12

## Context
We must ingest more records while the system stays live, show the progress of LLM structuring, and update
the analyst's 3 surfaces without downtime — and make the 1000-record scaling run demonstrable.

## Decision
Decouple the slow, rate-limited **ingest** path from the fast, deterministic **serving** path.
`POST /ingest` → `202 {job_id}` → **SQS** → rate-limited, **idempotent** workers (S3 cache-check dedups) →
per record: extract → validate → write S3 + INSERT into DuckDB + increment job counters; failures →
needs_review + **DLQ**. Progress via **polling** `GET /jobs/{id}`; analytics **poll-while-active** so the
board re-ranks live (the batch-health strip is the live progress surface). An **in-process asyncio worker**
is the drop-in fallback behind the same `extract()` interface.

## Alternatives
- **Synchronous blocking ingest** — freezes the UI, no live progress. Rejected.
- **No queue** — loses decoupling, idempotency, and the AWS scale story. Rejected (SQS is welcomed by the brief).

## Consequences
- + Zero-downtime live ingest; the 1000-record demo centerpiece; clean real-AWS map (Lambda/DLQ/DynamoDB).
- − Largest add beyond the core loop — the in-process fallback bounds the risk under the 8–12h budget.
