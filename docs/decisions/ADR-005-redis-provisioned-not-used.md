# ADR-005: Redis is provisioned now, not consumed yet

## Status
Accepted (Milestone 1)

## Context
Spec section 29 allows including Redis if justified for caching, rate
limiting, or future background jobs, but explicitly warns against
introducing it "if Redis is not actually being used yet" without
explaining its purpose. Spec section 28 similarly warns against adding
Celery "merely because it looks impressive."

## Decision
`docker-compose.yml` includes a `redis` service, but nothing in the
Django application currently reads from or writes to it. No cache backend
is configured in `settings`, no rate-limiting middleware is wired up.

## Why
Redis is provisioned early because the infrastructure shape (one more
`docker-compose` service, one more `REDIS_URL` env var) is cheap to add
now and expensive to bolt on later once the dev workflow is established.
But per spec sections 28-29, it is not being used for anything yet — that
would be scope creep with no current requirement driving it.

## Consequence
`REDIS_URL` exists in `.env.example` but nothing reads it yet. Treat this
as reserved infrastructure, not a working feature.

## Revisit
When a concrete need shows up — e.g. login rate limiting (spec section 26)
during Milestone 2, or dashboard/report caching (spec section 17) during
Milestone 7 — implement it against this already-provisioned Redis
instance rather than re-deciding whether to add Redis at that point.
