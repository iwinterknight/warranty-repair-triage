"""Curated query objects for analyst cold-start (Decision E / ADR-0006).

A preset *is* a saved query object — the same contract the query panel builds and `POST /aggregate` runs.
These are what greet the analyst on load; the CR-V infotainment cluster surfaces via `headline_board`.
"""
from __future__ import annotations

from typing import Any

PRESETS: dict[str, dict[str, Any]] = {
    # The money view: what's failing & clustering, severity-dominant priority ranking.
    "headline_board": {
        "group_by": ["subsystem", "model", "model_year"],
        "measure": {"signal": "priority"},
        "rank": {"by": "measure", "dir": "desc"},
    },
    # Warranty exposure: coverage mix per subsystem.
    "warranty_lens": {
        "group_by": ["subsystem", "warranty_status"],
        "measure": {"signal": "count"},
        "rank": {"by": "measure", "dir": "desc"},
    },
    # Watch cohort: the benign-looking leading edge (intermittent faults).
    # NOTE: the full cohort is intermittent ∧ (nff ∨ repeat_visit); the OR needs richer filter grammar —
    # the intermittent flag is the primary signal and is shipped; the compound refinement is a TODO.
    "watch_cohort": {
        "group_by": ["model", "model_year", "subsystem"],
        "filters": {"flags": {"intermittent": True}},
        "measure": {"signal": "count"},
        "rank": {"by": "measure", "dir": "desc"},
    },
}
