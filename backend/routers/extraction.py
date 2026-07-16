"""Extraction / ingest endpoints.

``/extract/run`` is the synchronous core-loop batch over the sample CSV (cache-first), with a live
progress counter the UI polls via ``/extract/status`` — a mini version of ADR-0008's job status until the
async ``/ingest`` + ``/jobs/{id}`` pipeline lands.
"""
from __future__ import annotations

import csv
from typing import Iterator

from fastapi import APIRouter, Request

from ..extract import extract_note
from ..providers import get_llm_client

router = APIRouter(tags=["extraction"])

IDLE_PROGRESS = {"active": False, "done": 0, "total": 0, "from_cache": 0, "needs_review": 0, "failed": 0}


def _read_csv(path: str) -> Iterator[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as fh:
        yield from csv.DictReader(fh)


@router.get("/extract/status")
def extract_status(request: Request) -> dict:
    """Live progress of the running batch (polled by the UI every few seconds)."""
    return getattr(request.app.state, "progress", IDLE_PROGRESS)


@router.post("/extract/run")
def extract_run(request: Request) -> dict:
    """Batch-extract the sample CSV, cache-first, then rebuild the DuckDB view so /aggregate reflects it."""
    st = request.app.state
    client = get_llm_client()

    rows = list(_read_csv(st.settings.data_csv_path))
    progress = {"active": True, "done": 0, "total": len(rows), "from_cache": 0, "needs_review": 0, "failed": 0}
    st.progress = progress

    processed = from_cache = needs_review = failed = 0
    try:
        for row in rows:
            passthrough = {k: row[k] for k in st.schema.passthrough_fields if k in row}
            record = extract_note(
                row["note_id"],
                row["technician_note"],
                passthrough,
                store=st.store,
                budget=st.budget,
                client=client,
                schema=st.schema,
                retry_cap=st.settings.retry_cap,
            )
            processed += 1
            if record["meta"].get("from_cache"):
                from_cache += 1
            if record["meta"].get("needs_review"):
                if record.get("extraction") is not None:
                    needs_review += 1   # persisted, quarantined → visible in the Review Queue
                else:
                    failed += 1         # transient (provider quota / network) → NOT cached, retries next run
            progress.update(done=processed, from_cache=from_cache, needs_review=needs_review, failed=failed)
            # Progressive refresh: rebuild the view every few records so the dashboard fills in live
            # during a batch instead of all-at-end (poor-man's ADR-0008 until async ingest exists).
            if processed % 5 == 0:
                st.engine.build_from_records(st.store.list_extractions())
    finally:
        st.progress = {**progress, "active": False}

    rows_in_view = st.engine.build_from_records(st.store.list_extractions())  # refresh derived view
    used = st.store.get_budget_used()
    return {
        "processed": processed,
        "from_cache": from_cache,
        "needs_review": needs_review,
        "failed_transient": failed,   # provider limits / network — retry on the next run at no extra cost
        "rows_in_view": rows_in_view,
        "budget_used": used,
        "budget_remaining": max(0, st.settings.max_requests_per_day - used),
    }
