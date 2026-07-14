"""Analytics endpoints — the 3 surfaces (presets, query panel, drill-down) over one query engine.

Everything here is deterministic and LLM-free: it reads the DuckDB view (Decision E).
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException

from ..deps import get_engine, get_store
from ..presets import PRESETS
from ..query_engine import QueryEngine
from ..store_s3 import S3Store

router = APIRouter(tags=["analytics"])


@router.post("/aggregate")
def aggregate(
    query: dict[str, Any] = Body(..., description="Query object: group_by / filters / measure / rank / top_k"),
    engine: QueryEngine = Depends(get_engine),
) -> dict:
    """One endpoint for presets, the query panel, and the visuals — all emit the same query object."""
    try:
        return engine.run(query)
    except ValueError as e:  # bad field / measure → client error, not a 500
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/presets")
def presets() -> dict:
    return PRESETS


@router.get("/extractions")
def list_extractions(
    store: S3Store = Depends(get_store),
    needs_review: Optional[bool] = None,
    subsystem: Optional[str] = None,
    model: Optional[str] = None,
) -> list[dict]:
    """Drill-down list with light filters (subsystem/model/needs_review)."""
    def keep(r: dict) -> bool:
        e = r.get("extraction") or {}
        m = r.get("meta") or {}
        p = r.get("passthrough") or {}
        if needs_review is not None and bool(m.get("needs_review")) != needs_review:
            return False
        if subsystem and e.get("subsystem") != subsystem:
            return False
        if model and p.get("model") != model:
            return False
        return True

    return [r for r in store.list_extractions() if keep(r)]


@router.get("/extractions/{note_id}")
def get_extraction(note_id: str, store: S3Store = Depends(get_store)) -> dict:
    rec = store.get_extraction(note_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"no extraction for {note_id}")
    return rec


@router.get("/review-queue")
def review_queue(store: S3Store = Depends(get_store)) -> list[dict]:
    """The honesty surface: low-confidence / validation-failed rows, excluded from aggregates by default."""
    return [r for r in store.list_extractions() if (r.get("meta") or {}).get("needs_review")]
