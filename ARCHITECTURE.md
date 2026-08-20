# Architecture — Humatan CRM

## Overview

Humatan CRM is a multi-tenant SaaS CRM backend built with Django + Django
REST Framework, backed by PostgreSQL. This document covers the
architecture as it stands after **Milestone 1 — Project Foundation**.

```
Client
  |
Django / DRF
  |
Authentication (JWT — Milestone 2)
  |
Tenant Resolution (Milestone 2)
  |
Authorization / RBAC (Milestone 6)
  |
Business Logic (services / selectors — Milestone 3+)
  |
PostgreSQL
```

## App layout

```
apps/
  core/       shared infrastructure: base models, tenant-isolation
              primitives, exception handling. No business-domain models.
  accounts/   identity & access: User, Role, Membership.
  tenants/    Tenant (company/organization) records.
```

Per spec section 3, `customers`, `leads`, `activities`, and `audit` apps
are intentionally not created yet — they arrive in later milestones and
will live in a single `customers` app internally organized into
models/serializers/views/services/selectors/filters submodules, per spec
section 4, rather than one flat file each.

## Multi-tenancy model

**Shared database, shared schema, tenant foreign key isolation** (spec
section 8) — every tenant-owned model carries an explicit `tenant` FK
rather than using separate databases or schemas per tenant.

### The isolation primitive: `TenantOwnedModel`

`apps/core/models.py` defines:

- `TimeStampedModel` — abstract `created_at`/`updated_at`.
- `TenantOwnedModel(TimeStampedModel)` — abstract base adding a `tenant`
  FK and a `TenantScopedManager` default manager. Every current
  (`Membership`) and future (`Customer`, `Lead`, `Deal`, `Activity`,
  `Task`, ...) tenant-owned model inherits from this instead of each app
  re-declaring its own `tenant` FK and re-implementing `.filter(tenant=...)`
  by hand in every selector.
- `TenantScopedQuerySet` — the query-level enforcement point, exposing:
  - `.for_tenant(tenant)` — explicit scoping, for platform-level code that
    legitimately operates on a specific tenant outside request context
    (management commands, admin actions).
  - `.scoped()` — scopes to whatever tenant is bound in the *current
    context* (see below). **Raises `RuntimeError` if no tenant context is
    bound** — a missing scope call fails loudly rather than silently
    returning nothing or leaking all tenants' data. See ADR-004 for the
    full reasoning.

The bare manager (`Model.objects.all()`) is **never** auto-filtered. This
is a deliberate choice: it should be visibly obvious, at every call site,
whether a query is tenant-scoped.

### Tenant context

`apps/core/context.py` provides `tenant_context(tenant)` (a context
manager) and `get_current_tenant()` / `set_current_tenant()`, built on
`contextvars` (not thread-locals) so behavior is correct under both
sync/WSGI and async/ASGI.

**Milestone 1 ships only this primitive.** Wiring it up to real HTTP
requests — a `TenantResolutionMiddleware` that derives the tenant from
the authenticated user's active Membership and calls `tenant_context(...)`
around the view — is Milestone 2 work (spec section 45), once
authentication exists to resolve a tenant *from*. Building the
middleware before authentication exists would mean either mocking
identity or guessing at the auth-to-tenant resolution flow prematurely.

## Identity & RBAC foundation

```
User -> Membership -> Tenant
           |
         Role
```

- `User` (`apps/accounts/models.py`) — platform-wide identity, email-based
  auth (`USERNAME_FIELD = "email"`). Not scoped to a single tenant — a
  `User` may hold Memberships in more than one `Tenant`.
- `Role` — a minimal, fixed lookup table for now (owner, sales_manager,
  sales_representative, support, viewer). See ADR-003 for why the full
  `Permission` model is deferred to Milestone 6.
- `Membership` — links `User` + `Tenant` + `Role`. A DB-level
  `UniqueConstraint` on `(user, tenant)` guarantees at most one Membership
  per user per tenant — enforced by PostgreSQL, not just application code
  (spec section 22), because an application-only check has a race
  condition under concurrent requests that the DB constraint does not.

`is_staff`/`is_superuser` on `User` (from Django's `PermissionsMixin`)
grant Django-admin/platform-operator access only, and are never used in
tenant-facing business authorization. See ADR-002.

## API surface

All API routes are versioned under `/api/v1/` (`config/api_urls.py`),
so a future `/api/v2/` can be introduced without restructuring every
app's internal `urls.py`. `apps/accounts/urls.py` and
`apps/tenants/urls.py` currently export empty `urlpatterns` — real
endpoints (auth, tenant management) land in Milestone 2.

Error responses are normalized by `apps/core/exceptions.py` into:

```json
{
  "detail": "Human-readable summary.",
  "code": "some_error_code",
  "errors": { "field_name": ["..."] }
}
```

regardless of whether the underlying DRF exception produced a plain
string, a list, or a nested dict.

## What's deliberately NOT built yet

Per spec sections 2, 40, and the milestone plan:

- No `Customer`, `Lead`, `Deal`, `Activity`, `Task`, or `Audit` models —
  Milestones 3, 4, 5, 8.
- No `Permission` model or scope (OWN/TEAM/TENANT) enforcement —
  Milestone 6.
- No authentication endpoints or `TenantResolutionMiddleware` —
  Milestone 2.
- No loyalty/rewards/marketing-automation/customer-portal features — out
  of scope per spec section 2 unless explicitly requested later.

## Milestone 1 architecture review

Per spec section 54:

1. **What did we build?** Repo/settings scaffolding, PostgreSQL wiring,
   Docker dev environment, `core`/`accounts`/`tenants` apps, `User`,
   `Role`, `Tenant`, `Membership` models, the centralized tenant-isolation
   primitive (`TenantOwnedModel`/`TenantScopedQuerySet`/`tenant_context`),
   a normalized API error format, CI, and initial tests.
2. **Why this design?** See ADR-001 through ADR-005.
3. **Security risks?** None of this milestone's code is internet-facing
   yet (no auth endpoints, no tenant-scoped views) — the main risk is
   architectural: if a future call site uses `Model.objects.all()`
   directly on a `TenantOwnedModel` instead of `.scoped()`/`.for_tenant()`,
   it silently returns cross-tenant data. This is mitigated by the design
   (raising on missing context) and must continue to be caught in code
   review and the Milestone 3+ isolation test suite (spec section 62).
4. **Performance risks?** None yet — no list/detail endpoints exist to
   have N+1 problems. Worth tracking once Milestone 3 introduces
   `Customer`/`Lead` list views.
5. **Technical debt?** `Role` has no `Permission` relation yet (ADR-003,
   intentional). No `TenantResolutionMiddleware` yet (intentional,
   Milestone 2).
6. **What should NOT be changed?** The `TenantOwnedModel` abstraction and
   its explicit-scoping design (ADR-004) — this is the foundation every
   future domain model will build on.
7. **What should be improved later?** Once enough tenant-owned models
   exist, consider a lint/check rule that flags unscoped queryset access
   on `TenantOwnedModel` subclasses (see ADR-004 "Revisit").
8. **Over-engineering?** `TenantScopedQuerySet`/`TenantOwnedModel` is more
   abstraction than Milestone 1 strictly needs (only `Membership` uses it
   so far) — accepted deliberately, since retrofitting it after
   `Customer`/`Lead`/`Deal` exist would be far more invasive. See the
   architecture recommendation this was based on.
9. **Is tenant isolation guaranteed?** For the one tenant-owned model that
   exists (`Membership`), yes — verified by
   `apps/core/tests/test_tenant_isolation_foundation.py`. Nothing is yet
   guaranteed for future models beyond "they'll inherit the same
   mechanism."
10. **Are tests covering critical behavior?** Yes for what exists this
    milestone: user creation/uniqueness, membership uniqueness
    constraint, cross-tenant membership isolation, and the
    `tenant_context`/`scoped()`/`for_tenant()` mechanics themselves (24
    tests, all passing against a real PostgreSQL instance).
