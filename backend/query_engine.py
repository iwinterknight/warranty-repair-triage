"""Aggregation query engine — grammar → parameterized DuckDB SQL (Decision E / ADR-0006).

The query object (Group / Filter / Measure / rank / top_k) is a *logical plan*; this compiles it to
**parameterized** DuckDB SQL and runs it over a table materialized from the cached extraction records.

Safety: group/filter field names are validated against a fixed whitelist derived from the schema's
dimensions (a safe DSL — never string-interpolated user input); values bind as query parameters; numeric
weights are coerced to float. S3 = truth, DuckDB = derived view — ``build_from_records()`` (re)materializes
the table on load and as ingest lands (Decision G).
"""
from __future__ import annotations

from typing import Any, Optional

import duckdb

_FLAGS = ["safety_related", "vehicle_disabled", "repeat_visit",
          "customer_distress", "fleet_signal", "intermittent"]

_INSERT_COLS = [
    "note_id", "date", "model", "model_year", "mileage", "complaint_summary", "component_mention",
    "subsystem", "warranty_status", "denial_reason", "resolution_status", "severity", "confidence",
    "evidence_quote", *_FLAGS, "needs_review", "schema_version", "model_used",
]

_TABLE_DDL = """
CREATE TABLE extractions (
  note_id VARCHAR, date VARCHAR, model VARCHAR, model_year INTEGER, mileage INTEGER,
  complaint_summary VARCHAR, component_mention VARCHAR, subsystem VARCHAR,
  warranty_status VARCHAR, denial_reason VARCHAR, resolution_status VARCHAR,
  severity VARCHAR, confidence VARCHAR, evidence_quote VARCHAR,
  safety_related BOOLEAN, vehicle_disabled BOOLEAN, repeat_visit BOOLEAN,
  customer_distress BOOLEAN, fleet_signal BOOLEAN, intermittent BOOLEAN,
  needs_review BOOLEAN, schema_version VARCHAR, model_used VARCHAR
)
"""

# Whitelists — the SQL-injection guard. Only these names may be templated into SQL.
_DIMENSIONS = {"model", "model_year", "subsystem", "warranty_status", "denial_reason",
               "resolution_status", "severity", "confidence", *_FLAGS}
_RANGE_COLS = {"model_year", "mileage"}
_MEASURES = {"count", "severity_index", "priority"}
_SEVERITIES = {"low", "medium", "high", "critical"}

# Default priority-score weights — SEVERITY-DOMINANT (ratified): the steep severity map means a single
# `critical` (64) outweighs 60 `low` notes; count/recency are secondary; safety/repeat/fleet are boosts.
DEFAULT_WEIGHTS: dict[str, Any] = {
    "severity_map": {"low": 1, "medium": 4, "high": 16, "critical": 64},
    "w_severity": 1.0, "w_count": 1.0, "w_recency": 5.0,
    "boost_safety": 25.0, "boost_repeat": 5.0, "boost_fleet": 8.0,
}


def _i(v: Any) -> Optional[int]:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def flatten(record: dict[str, Any]) -> tuple:
    """One cached record → one flat row (unnest severity_flags, lift passthrough + meta)."""
    p = record.get("passthrough") or {}
    e = record.get("extraction") if isinstance(record.get("extraction"), dict) else {}
    e = e or {}
    f = e.get("severity_flags") or {}
    m = record.get("meta") or {}
    row = {
        "note_id": record.get("note_id"),
        "date": p.get("date"),
        "model": p.get("model"),
        "model_year": _i(p.get("model_year")),
        "mileage": _i(p.get("mileage")),
        "complaint_summary": e.get("complaint_summary"),
        "component_mention": e.get("component_mention"),
        "subsystem": e.get("subsystem"),
        "warranty_status": e.get("warranty_status"),
        "denial_reason": e.get("denial_reason"),
        "resolution_status": e.get("resolution_status"),
        "severity": e.get("severity"),
        "confidence": e.get("confidence"),
        "evidence_quote": e.get("evidence_quote"),
        **{fl: (bool(f[fl]) if fl in f and f[fl] is not None else None) for fl in _FLAGS},
        "needs_review": bool(m.get("needs_review", False)),
        "schema_version": m.get("schema_version"),
        "model_used": m.get("model"),
    }
    return tuple(row[c] for c in _INSERT_COLS)


# --- SQL fragment builders ---------------------------------------------------

def _sev_case(sev_map: dict[str, Any]) -> str:
    whens = " ".join(f"WHEN '{k}' THEN {float(v)}" for k, v in sev_map.items() if k in _SEVERITIES)
    return f"CASE severity {whens} ELSE 0 END"


def _priority_expr(w: dict[str, Any]) -> str:
    sev = _sev_case(w["severity_map"])
    gmax = "(SELECT max(CAST(date AS DATE)) FROM extractions)"
    span = ("(SELECT NULLIF(date_diff('day', min(CAST(date AS DATE)), "
            "max(CAST(date AS DATE))), 0) FROM extractions)")
    recency = f"(1 - date_diff('day', max(CAST(date AS DATE)), {gmax})::DOUBLE / {span})"
    return (
        f"({float(w['w_severity'])}*sum({sev})"
        f" + {float(w['w_count'])}*count(*)"
        f" + {float(w['w_recency'])}*coalesce({recency}, 0)"
        f" + {float(w['boost_safety'])}*sum(CASE WHEN safety_related THEN 1 ELSE 0 END)"
        f" + {float(w['boost_repeat'])}*sum(CASE WHEN repeat_visit THEN 1 ELSE 0 END)"
        f" + {float(w['boost_fleet'])}*sum(CASE WHEN fleet_signal THEN 1 ELSE 0 END))"
    )


def _measure_expr(signal: str, w: dict[str, Any]) -> str:
    if signal == "count":
        return "count(*)"
    if signal == "severity_index":
        return f"{_sev_case(w['severity_map'])}"  # placeholder replaced below
    return _priority_expr(w)


def _where(filters: dict[str, Any], params: list) -> str:
    clauses: list[str] = []
    if not filters.get("include_review", False):
        clauses.append("needs_review = FALSE")   # uncertainty contract: review rows excluded by default
    for key, val in filters.items():
        if key == "include_review":
            continue
        if key == "flags":
            for fl, b in val.items():
                if fl not in _FLAGS:
                    raise ValueError(f"unknown flag: {fl}")
                clauses.append(f"{fl} = ?")
                params.append(bool(b))
            continue
        if key in _RANGE_COLS and isinstance(val, (list, tuple)) and len(val) == 2:
            clauses.append(f"{key} BETWEEN ? AND ?")
            params.extend([val[0], val[1]])
            continue
        if key in _DIMENSIONS:
            if isinstance(val, (list, tuple)):
                clauses.append(f"{key} IN ({','.join(['?'] * len(val))})")
                params.extend(val)
            else:
                clauses.append(f"{key} = ?")
                params.append(val)
            continue
        raise ValueError(f"unknown filter field: {key}")
    return (" WHERE " + " AND ".join(clauses)) if clauses else ""


def compile_query(query: dict[str, Any]) -> tuple[str, list]:
    """Translate a query object into (parameterized SQL, params). The public contract of the engine."""
    group_by = list(query.get("group_by") or [])
    for g in group_by:
        if g not in _DIMENSIONS:
            raise ValueError(f"bad group_by field: {g}")

    signal = (query.get("measure") or {}).get("signal", "count")
    if signal not in _MEASURES:
        raise ValueError(f"unknown measure: {signal}")
    weights = {**DEFAULT_WEIGHTS, **((query.get("measure") or {}).get("weights") or {})}

    if signal == "severity_index":
        measure_sql = f"({_sev_case(weights['severity_map'])})::DOUBLE / NULLIF(count(*), 0)"
    else:
        measure_sql = _measure_expr(signal, weights)

    params: list = []
    where = _where(query.get("filters") or {}, params)
    rank = query.get("rank") or {}
    direction = "ASC" if str(rank.get("dir", "desc")).lower() == "asc" else "DESC"
    top_k = query.get("top_k") or {}

    # Population scalar (no group-by).
    if not group_by:
        return f"SELECT {measure_sql} AS measure FROM extractions{where}", params

    select_cols = ", ".join(group_by)
    base = f"SELECT {select_cols}, {measure_sql} AS measure FROM extractions{where} GROUP BY {select_cols}"

    # Nested top-k over exactly two group levels (e.g. top-10 models × top-3 subsystems).
    if len(group_by) == 2 and group_by[0] in top_k and group_by[1] in top_k:
        g0, g1 = group_by
        k0, k1 = int(top_k[g0]), int(top_k[g1])
        return (
            f"WITH base AS ({base}), "
            f"top0 AS (SELECT {g0}, sum(measure) AS m0 FROM base GROUP BY {g0} "
            f"QUALIFY row_number() OVER (ORDER BY m0 {direction}) <= {k0}) "
            f"SELECT b.{g0}, b.{g1}, b.measure FROM base b JOIN top0 t USING ({g0}) "
            f"QUALIFY row_number() OVER (PARTITION BY b.{g0} ORDER BY b.measure {direction}) <= {k1} "
            f"ORDER BY t.m0 {direction}, b.measure {direction}"
        ), params

    # Single-level: order by measure, optional overall limit.
    sql = f"{base} ORDER BY measure {direction}"
    limit = top_k.get(group_by[0]) if group_by else None
    if limit is not None:
        sql += f" LIMIT {int(limit)}"
    return sql, params


class QueryEngine:
    def __init__(self) -> None:
        self._con = duckdb.connect(database=":memory:")
        self._con.execute(_TABLE_DDL)

    def build_from_records(self, records: list[dict[str, Any]]) -> int:
        """(Re)materialize the derived view from cached records. Returns row count."""
        self._con.execute("DELETE FROM extractions")
        rows = [flatten(r) for r in records]
        if rows:
            placeholders = ",".join(["?"] * len(_INSERT_COLS))
            self._con.executemany(f"INSERT INTO extractions VALUES ({placeholders})", rows)
        return len(rows)

    def run(self, query: dict[str, Any]) -> dict[str, Any]:
        sql, params = compile_query(query)
        cur = self._con.execute(sql, params)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        return {"columns": cols, "rows": rows, "n": len(rows)}
