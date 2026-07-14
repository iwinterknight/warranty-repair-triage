# ADR-0007: Provider ladder + `LLM_PROVIDER` seam (Decision F)
- Status: Accepted — 2026-07-14
- Deciders: Sunit, Claude
- Related: SDD §7.2 · locked decision #10 · env contract §8

## Context
The build must run on the free tier; the scaling demo wants a real LLM + a genuine AWS story; and we may
later self-host. Config, not code, should choose the provider (the brief grades env-driven config).

## Decision
One `LLMClient` interface selected by env **`LLM_PROVIDER`**, with adapters: **openai_compat**
(`base_url`/`model`/`key` → covers **OpenRouter** and **vLLM**) and **bedrock** (boto3 `converse` →
**Claude on AWS**, managed/closed-weight — not vLLM). Ladder: **Phase 1 OpenRouter** (30 records) →
**Phase 2 Bedrock+Claude** (1000-record run, own key lifts the cap) → **Phase 3 Llama+vLLM** (RAG stretch).
Budgets/models never mix; `meta.model` keeps each set traceable.

## Alternatives
- **Single hardcoded provider** — no portability, no scaling/AWS story. Rejected.

## Consequences
- + Config-only portability (managed-free → managed-AWS → self-hosted); the 1000-record run uses a real LLM.
- − Bedrock isn't OpenAI-SDK-shaped → needs its own boto3 adapter (not a pure env swap); it's real AWS, not LocalStack.
