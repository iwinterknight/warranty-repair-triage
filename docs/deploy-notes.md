# Deploy Notes — Honda Warranty & Repair-Order Triage
Local-run (Docker Compose + LocalStack) and real-AWS mapping. Populated during build.

## Local (target)
- `docker compose up`: frontend (Next.js/React), backend (FastAPI), LocalStack (S3)
- All environment-specific config via env vars (`.env.example`): OPENROUTER_API_KEY, OPENROUTER_BASE_URL, LLM_MODEL, AWS_ENDPOINT_URL, S3_BUCKET, AWS creds (dummy for LocalStack)
- Clean-clone test is a hard gate before submission: fresh checkout + evaluator's own OpenRouter key must work exactly as README says. Reserve time at the end for this.
- Restart-safety: S3 extraction cache means container restarts consume zero LLM budget.

## Real-AWS mapping (to be written into README)
- LocalStack S3 → S3 (identical boto3 code; drop AWS_ENDPOINT_URL override)
- Backend container → ECS Fargate (or Lambda for batch extraction jobs)
- Optional: SQS for note-ingest queue at scale (decouples ingest from extraction under rate limits)
- Secrets → AWS Secrets Manager / SSM Parameter Store (replaces .env)
- Observability: extraction metadata already in S3; production adds CloudWatch metrics on validation-failure rate by model/subsystem
- (Role context: AWS AgentCore — deployment-plan section is the natural place to reference managed agent runtimes without over-building the prototype)

## Rate-limit posture
- 20 req/min → client-side throttle; 50 req/day → cache-first + capped retries (1) + `needs_review` fallback instead of retry loops
