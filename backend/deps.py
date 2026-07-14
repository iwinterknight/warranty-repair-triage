"""FastAPI dependency getters — pull the app-scoped resources built in ``app.py``'s lifespan.

Resources (S3 store, DuckDB engine, loaded schema, budget guard, settings) are constructed once at startup
and stashed on ``app.state``; routers depend on these getters rather than reaching for globals — keeps
handlers thin and testable.
"""
from __future__ import annotations

from fastapi import Request

from .budget import BudgetGuard
from .config import Settings
from .query_engine import QueryEngine
from .schema_loader import LoadedSchema
from .store_s3 import S3Store


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_store(request: Request) -> S3Store:
    return request.app.state.store


def get_engine(request: Request) -> QueryEngine:
    return request.app.state.engine


def get_schema(request: Request) -> LoadedSchema:
    return request.app.state.schema


def get_budget(request: Request) -> BudgetGuard:
    return request.app.state.budget
