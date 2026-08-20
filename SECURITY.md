# Security — Humatan CRM

This document describes the security model as it stands after
**Milestone 1 — Project Foundation**, and what's planned for later
milestones. It will be kept in sync as those milestones land.

## Threat model summary

Humatan CRM is a multi-tenant B2B SaaS CRM. The highest-priority threat is
**cross-tenant data exposure**: a user authenticated for Tenant A
retrieving, modifying, or inferring the existence of Tenant B's data
(customers, leads, deals, activities, tasks). Spec section 62 makes this
the single highest-priority test area in the whole project, and this
document treats it the same way.

## Tenant isolation

- **Mechanism**: shared database, shared schema, explicit `tenant`
  foreign key on every tenant-owned model (spec section 8). See
  `ARCHITECTURE.md` for the full `TenantOwnedModel`/`TenantScopedQuerySet`
  design and ADR-004 for why scoping is explicit rather than automatic.
- **Never trust a client-supplied tenant ID.** No endpoint accepts a
  `tenant_id` parameter from the client and uses it for authorization.
  Tenant context must always be derived from the authenticated identity
  (the user's active Membership), never from request input. This applies
  to every surface listed in spec section 9: list, detail, update, delete,
  search, filtering, ordering, related/nested objects, reports, exports,
  bulk operations, and background tasks.
- **Current status (Milestone 1)**: the isolation *primitive* exists and
  is tested (`apps/core/tests/test_tenant_isolation_foundation.py`), but
  no HTTP-facing views exist yet to enforce it end-to-end — that begins
  in Milestone 2 with `TenantResolutionMiddleware` and continues through
  Milestone 3+ as `Customer`/`Lead`/`Deal` views are built. Until then,
  there is no tenant-isolation *attack surface* to test at the HTTP
  level; the isolation test suite covering full request/response cycles
  (spec section 62) will be built alongside those endpoints.

## Authentication vs. authorization vs. tenant resolution

Kept as three distinct concerns (spec section 25), each answering a
different question:

| Concern | Question | Where |
|---|---|---|
| Authentication | "Who are you?" | JWT (djangorestframework-simplejwt) — Milestone 2 |
| Tenant resolution | "Which organization are you operating in?" | `TenantResolutionMiddleware` + `tenant_context` — Milestone 2 |
| Authorization | "What are you allowed to do?" | Membership -> Role -> Permission — Milestone 6 |

## Platform superuser vs. tenant RBAC

Django's `is_staff`/`is_superuser` grant Django-admin access only, and are
never checked in tenant-facing business authorization logic. See ADR-002.
This means a platform operator with Django-admin access does not
implicitly gain business permissions inside a tenant's CRM data — those
are different concerns.

## Database-level integrity, not just application-level

Per spec section 22, constraints the database can guarantee are enforced
at the database level rather than relying solely on application checks
that have race conditions under concurrent requests:

- `Membership`: `UniqueConstraint(fields=["user", "tenant"])` — at most
  one Membership per user per tenant.
- `User.email`: unique, case-normalized via `normalize_email`.
- `Tenant.slug`: unique.

## Secrets & configuration

- No secrets are committed. `.env` is gitignored; `.env.example` ships
  with placeholder values only.
- `SECRET_KEY`, database credentials, and JWT lifetimes are all read from
  environment variables via `django-environ` (`config/settings/base.py`).
- `config/settings/production.py` hard-disables `DEBUG` regardless of the
  `DJANGO_DEBUG` env var's value, so a misconfigured environment variable
  cannot accidentally enable debug mode (which would leak stack
  traces/settings) in production.
- `production.py` also requires `DJANGO_ALLOWED_HOSTS` to be set
  explicitly (raises `RuntimeError` at startup if empty) rather than
  silently falling back to an unsafe default.

## Production hardening (`config/settings/production.py`)

- `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` —
  all enabled, assuming the deployment sits behind HTTPS-terminating
  infrastructure (spec section 65's reverse-proxy assumption).
- `SECURE_HSTS_SECONDS` (30 days), `SECURE_HSTS_INCLUDE_SUBDOMAINS`,
  `SECURE_HSTS_PRELOAD` — enabled.
- `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS = "DENY"` — enabled.
- `SECURE_PROXY_SSL_HEADER` — configured for a standard
  `X-Forwarded-Proto` reverse-proxy setup.
- The browsable API renderer is disabled in production (JSON only) to
  reduce accidental information exposure through DRF's default HTML UI.

## Authentication (planned — Milestone 2)

- JWT via `djangorestframework-simplejwt`, already installed and
  configured in `settings.SIMPLE_JWT` (short-lived access tokens,
  rotating refresh tokens with blacklist-after-rotation).
- Brute-force protection / login rate limiting is not yet implemented;
  planned against the already-provisioned Redis instance (see ADR-005)
  once login endpoints exist.

## API error responses

`apps/core/exceptions.py` normalizes every DRF error into a consistent
`{"detail", "code", "errors"}` shape, so API consumers can't accidentally
rely on inconsistent error shapes that might otherwise leak
implementation details differently across endpoints.

## What's out of scope for this document today

Object-level permissions, CORS configuration specifics, rate limiting,
file-upload handling, and CSRF specifics for the API will be documented
as they're implemented in later milestones (2, 5, 6, 9) rather than
speculatively described now.
