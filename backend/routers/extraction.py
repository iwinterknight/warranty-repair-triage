"""Extraction / ingest endpoints.

``/extract/run`` is the synchronous core-loop batch over the sample CSV (cache-first). The async
``/ingest`` + ``/jobs/{id}`` (Decision G) land with the ingest pipeline.
"""
from __future__ import annotations

import csv
from typing import Iterator

from fastapi import APIRouter, Request

from ..extract import extract_note
from ..providers import get_llm_client

router = APIRouter(tags=["extraction"])


def _read_csv(path: str) -> Iterator[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as fh:
        yield from csv.DictReader(fh)


@router.post("/extract/run")
def extract_run(request: Request) -> dict:
    """Batch-extract the sample CSV, cache-first, then rebuild the DuckDB view so /aggregate reflects it."""
    st = request.app.state
    client = get_llm_client()

    processed = from_cache = needs_review = 0
    for row in _read_csv(st.settings.data_csv_path):
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
            needs_review += 1
        # Progressive refresh: rebuild the view every few records so the dashboard fills in live
        # during a batch instead of all-at-end (poor-man's ADR-0008 until async ingest exists).
        if processed % 5 == 0:
            st.engine.build_from_records(st.store.list_extractions())

    rows_in_view = st.engine.build_from_records(st.store.list_extractions())  # refresh derived view
    used = st.store.get_budget_used()
    return {
        "processed": processed,
        "from_cache": from_cache,
        "needs_review": needs_review,
        "rows_in_view": rows_in_view,
        "budget_used": used,
        "budget_remaining": max(0, st.settings.max_requests_per_day - used),
    }
