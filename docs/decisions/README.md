# Architecture Decision Records (ADRs)

One short, **immutable**, numbered file per consequential decision. An ADR records *why* we chose
something, the alternatives, and the consequences — the decision trail that the SDD (the *how*) and
CLAUDE.md (the terse locked index) don't preserve.

**Rules**
- An **Accepted** ADR is never edited. If a decision changes, write a **new** ADR and mark the old one
  `Superseded by ADR-00XX`. The trail is the value.
- The SDD holds the living "how it's built"; ADRs hold the frozen "why we decided this." SDD sections
  cross-link to ADRs; ADRs cross-link to SDD sections.
- Keep each ADR short (~15–20 lines). If it needs more, it belongs in the SDD.

**Template**
```
# ADR-000X: <title>
- Status: Proposed | Accepted | Superseded by ADR-00Y — <date>
- Deciders: <who>
- Related: SDD §X · ADR-000Z

## Context      — the forces/constraints that made a decision necessary
## Decision     — what we chose (imperative, specific)
## Alternatives — what we rejected and why
## Consequences — + gains / − costs & things to watch
```

**Index**
| ADR | Decision | SDD | Status |
|---|---|---|---|
| [0001](0001-adopt-adrs-and-self-composing-docs.md) | Adopt ADRs + self-composing modular docs | §2, docs/README.md | Accepted |
| [0002](0002-s3-key-layout-and-provenance.md) | S3 key layout + provenance stamp (Decision A) | §4 | Accepted |
| [0003](0003-compute-on-read-aggregates.md) | Compute-on-read aggregates (Decision B) | §5 | Accepted (refined by 0006) |
| [0004](0004-prompt-design.md) | Schema-driven prompt design (Decision C) | §6 | Accepted |
| [0005](0005-aggregate-first-dashboard.md) | Aggregate-first dashboard + review queue (Decision D) | §7 | Accepted |
| [0006](0006-aggregation-grammar-duckdb.md) | Aggregation-as-one-grammar, DuckDB (Decision E) | §7.1 | Accepted |
| [0007](0007-provider-ladder-seam.md) | Provider ladder + `LLM_PROVIDER` seam (Decision F) | §7.2 | Accepted |
| [0008](0008-async-ingest-pipeline.md) | Async ingest / live-progress pipeline (Decision G) | §7.3 | Accepted |

Foundational **locked** decisions (warranty 4-state, S3-as-cache, schema-driven, one-call-per-note, …)
are indexed in [`../../CLAUDE.md`](../../CLAUDE.md); promote any to a full ADR if it later needs revisiting.
