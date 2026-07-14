"""Deterministic, no-LLM tests for the aggregation engine (SDD §11).

Seeds fixture extraction records straight into the DuckDB view and asserts the analytics behave — most
importantly that the planted **CR-V infotainment cluster ranks #1** on the headline board. Runs with only
``duckdb`` installed: ``python tests/test_aggregate.py`` (also pytest-discoverable).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.presets import PRESETS
from backend.query_engine import QueryEngine

_FLAGS = ["safety_related", "vehicle_disabled", "repeat_visit",
          "customer_distress", "fleet_signal", "intermittent"]


def _rec(note_id, date, model, year, mileage, subsystem, warranty, severity,
         *, flags=(), resolution="repaired", needs_review=False):
    flag_obj = {f: (f in flags) for f in _FLAGS}
    extraction = None if needs_review else {
        "complaint_summary": f"{subsystem} issue",
        "component_mention": subsystem,
        "subsystem": subsystem,
        "warranty_status": warranty,
        "denial_reason": None,
        "resolution_status": resolution,
        "severity": severity,
        "severity_flags": flag_obj,
        "confidence": "high",
        "evidence_quote": "x",
    }
    return {
        "note_id": note_id,
        "passthrough": {"date": date, "model": model, "model_year": year, "mileage": mileage},
        "extraction": extraction,
        "meta": {"schema_version": "0.2.0", "needs_review": needs_review, "model": "test"},
    }


def _fixtures():
    return [
        # The planted CR-V infotainment cluster (RO-100001/6/10/16/26).
        _rec("RO-100001", "2026-05-28", "CR-V", 2022, 14230, "infotainment_electronics", "undetermined",
             "high", flags=("intermittent",), resolution="escalated"),
        _rec("RO-100006", "2026-05-12", "CR-V", 2022, 18760, "infotainment_electronics", "covered",
             "medium", flags=("fleet_signal",)),
        _rec("RO-100010", "2026-06-15", "CR-V", 2023, 12050, "infotainment_electronics", "covered",
             "medium", flags=("repeat_visit", "customer_distress")),
        _rec("RO-100016", "2026-06-20", "CR-V", 2024, 2100, "infotainment_electronics", "undetermined",
             "medium", flags=("fleet_signal", "customer_distress", "intermittent"), resolution="monitoring"),
        _rec("RO-100026", "2026-06-22", "CR-V Hybrid", 2023, 11900, "infotainment_electronics",
             "undetermined", "high", flags=("safety_related",), resolution="monitoring"),
        # Non-cluster background noise.
        _rec("RO-100002", "2026-04-08", "Accord", 2019, 68540, "brakes", "denied", "low"),
        _rec("RO-100003", "2026-06-02", "Civic", 2023, 9110, "hvac", "covered", "low"),
        _rec("RO-100028", "2026-06-03", "Pilot", 2022, 19800, "tires_wheels", "covered", "low"),
        # A needs_review row — must be excluded from aggregates by default.
        _rec("RO-BAD", "2026-06-01", "CR-V", 2022, 5000, "infotainment_electronics", "undetermined",
             "critical", needs_review=True),
    ]


def _engine():
    e = QueryEngine()
    e.build_from_records(_fixtures())
    return e


def test_headline_cluster_ranks_first():
    res = _engine().run(PRESETS["headline_board"])
    top = res["rows"][0]
    assert top["subsystem"] == "infotainment_electronics", f"expected infotainment on top, got {top}"
    assert top["model"] in ("CR-V", "CR-V Hybrid"), f"expected a CR-V on top, got {top}"
    print(f"  headline top row: {top}")


def test_needs_review_excluded_by_default():
    # RO-BAD is critical CR-V infotainment but needs_review → must not appear.
    res = _engine().run({"group_by": ["subsystem"], "measure": {"signal": "count"}})
    total = sum(r["measure"] for r in res["rows"])
    assert total == 8, f"expected 8 aggregated (9 fixtures - 1 needs_review), got {total}"


def test_warranty_lens_runs():
    res = _engine().run(PRESETS["warranty_lens"])
    assert res["n"] > 0 and "warranty_status" in res["columns"]


def test_watch_cohort_intermittent():
    res = _engine().run(PRESETS["watch_cohort"])
    # RO-100001 and RO-100016 carry intermittent.
    assert res["n"] >= 1, "watch cohort should surface intermittent notes"


def test_nested_topk_smoke():
    res = _engine().run({
        "group_by": ["model", "subsystem"],
        "measure": {"signal": "count"},
        "rank": {"by": "measure", "dir": "desc"},
        "top_k": {"model": 10, "subsystem": 3},
    })
    assert res["n"] >= 1 and {"model", "subsystem"} <= set(res["columns"])


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\nAll {len(tests)} aggregation tests passed.")
