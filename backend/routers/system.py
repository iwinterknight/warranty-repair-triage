"""System / meta endpoints: liveness, active schema (transparency), budget remaining."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..budget import BudgetGuard
from ..config import Settings
from ..deps import get_budget, get_schema, get_settings_dep
from ..schema_loader import LoadedSchema

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/schema")
def active_schema(schema: LoadedSchema = Depends(get_schema)) -> dict:
    """Expose the active schema + version — the pipeline is schema-driven, so this is the live contract."""
    return {"version": schema.version, "schema": schema.json_schema}


@router.get("/budget")
def budget(
    guard: BudgetGuard = Depends(get_budget),
    settings: Settings = Depends(get_settings_dep),
) -> dict:
    used = guard._store.get_budget_used()  # read-only peek at the daily ledger
    limit = settings.max_requests_per_day
    return {"used": used, "limit": limit, "remaining": max(0, limit - used)}
