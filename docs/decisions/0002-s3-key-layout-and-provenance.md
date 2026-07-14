# ADR-0002: S3 key layout + provenance stamp (Decision A)
- Status: Accepted — 2026-07-14
- Deciders: Sunit, Claude
- Related: SDD §4 · locked decision #2 (S3 = load-bearing cache)

## Context
S3 is the load-bearing extraction cache **and** the audit trail. It needs: cheap restart (0 LLM calls),
a version-safety guard so a schema bump or edited note re-extracts, and a git↔runtime provenance link.

## Decision
Flat, note-addressed records: `extractions/{note_id}.json` + `_budget/{YYYY-MM-DD}.json` (daily ledger).
Cache-hit requires `schema_version` **and** `note_sha256` to match current. The per-object `meta` block is
the audit trail and stamps `model` / `prompt_version` / `git_sha` — provenance that traces any output to
the exact commit, schema, and prompt. Provenance fields are **excluded from the cache-hit check** (a
rebuild at the same schema+prompt must not bust the cache).

## Alternatives
- **Version in the path** (`extractions/{schema_version}/{note_id}.json`) — cleaner isolation but scatters
  the corpus and forces aggregation to know which prefix to read. Rejected for the prototype.

## Consequences
- + Restart / re-run costs 0 LLM budget; full auditable provenance per record.
- − A single flat prefix to list (fine at prototype scale).
