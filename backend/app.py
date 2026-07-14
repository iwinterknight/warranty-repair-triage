"""FastAPI application — thin composition root.

Startup builds the app-scoped resources once (S3 store + bucket, active schema, DuckDB view materialized
from cached records, budget guard) and stashes them on ``app.state``; routers depend on them via ``deps``.
Routers are split by domain (analytics / extraction / system) so the auto-generated ``/docs`` reads as
grouped sections.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .budget import BudgetGuard
from .config import get_settings
from .query_engine import QueryEngine
from .routers import analytics, extraction, system
from .schema_loader import load_schema
from .store_s3 import S3Store


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    store = S3Store()
    store.ensure_bucket()                      # idempotent — clean clone just works
    engine = QueryEngine()
    engine.build_from_records(store.list_extractions())  # S3 = truth → DuckDB derived view (0 LLM calls)

    app.state.settings = settings
    app.state.store = store
    app.state.schema = load_schema()
    app.state.engine = engine
    app.state.budget = BudgetGuard(store)
    yield


app = FastAPI(title="Warranty & Repair-Order Triage", version="0.1.0", lifespan=lifespan)

# Dev CORS: the React (Vite) frontend calls the backend across ports.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)
app.include_router(analytics.router)
app.include_router(extraction.router)
