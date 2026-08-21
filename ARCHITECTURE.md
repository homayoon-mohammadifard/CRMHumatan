# Architecture — Humatan CRM

## Overview

Humatan CRM is a multi-tenant SaaS CRM backend built with Django + Django
REST Framework, backed by PostgreSQL. This document covers the
architecture as it stands after **Milestone 2 — Authentication + Tenant
Access**.

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
app's internal `urls.py`.

### Authentication (Milestone 2)
- `POST /api/v1/auth/register/` — signup new company (creates User +
  Tenant + owner Membership atomically)
- `POST /api/v1/auth/login/` — email+password → access+refresh JWT tokens
- `POST /api/v1/auth/logout/` — blacklist refresh token
- `POST /api/v1/auth/token/refresh/` — obtain new access token from
  refresh token
- `GET /api/v1/auth/me/` — authenticated user's identity + all tenant
  memberships (not tenant-scoped)

### Tenant management (Milestone 2)
- `GET /api/v1/tenants/` — user's memberships across all tenants + their
  role in each (not tenant-scoped; shows all of the user's organizations)
- `GET /api/v1/tenants/me/` — current active tenant details (requires
  `X-Tenant-ID` header + valid membership)
- `PATCH /api/v1/tenants/me/` — update current tenant (owner-only; requires
  `X-Tenant-ID` header)

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
- No CRM domain endpoints — Milestone 3+.
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

## Milestone 2 architecture review

Per spec section 54:

1. **What did we build?** JWT authentication (register/login/logout/token
   refresh), an authenticated user's identity endpoint, tenant
   list/current-tenant endpoints, `TenantResolutionMiddleware`, basic
   authorization primitives (`HasActiveTenant`, `IsTenantOwner`), and 36
   new tests covering auth flows, tenant management, and high-priority
   tenant-isolation scenarios.
2. **Why this design?** See the module docstrings in `apps/accounts/middleware.py`
   and `apps/tenants/views.py` for the reasoning behind JWT payload shape
   (no tenant claim; resolution via X-Tenant-ID header + cross-validation
   against Membership rows) and why `X-Tenant-ID` is a *hint* never
   trusted for authorization (spec sections 8, 9). The permission classes
   (`HasActiveTenant`, `IsTenantOwner`) are minimal and intentionally not
   tied to a full Permission model yet (that's Milestone 6).
3. **Security risks?** Tenant resolution middleware correctly enforces that
   a user can only select a tenant they have an active Membership in, via
   database lookup rather than trusting the header. All tenant-scoped
   endpoints now require `HasActiveTenant` permission. The isolated risk
   is whether a future endpoint forgets to add these permissions — this is
   mitigated by the pattern being established here and enforced in code
   review.
4. **Performance risks?** `TenantResolutionMiddleware` runs JWT decode on
   every request (cached by DRF's authentication machinery), then a
   Membership lookup with `select_related("tenant", "role")`. For the
   endpoint-level read volumes expected, this is acceptable. Worth
   profiling at scale once Milestone 3+ domain endpoints exist.
5. **Technical debt?** `Role` still has no `Permission` relation (ADR-003,
   intentional for Milestone 6). `IsTenantOwner` is hard-coded to check
   `role.slug == Role.Slug.OWNER`; this should be table-driven once the
   Permission model exists.
6. **What should NOT be changed?** The tenant resolution design (X-Tenant-ID
   header + cross-validation against Membership rows, never trusting
   client-supplied ID for authorization). The `TenantOwnedModel` foundation
   from Milestone 1 is now proven correct by the auth flow using it
   (`Membership`).
7. **What should be improved later?** Once Milestone 3 introduces
   `Customer`/`Lead` domain endpoints, ensure each one adds
   `HasActiveTenant` to its permissions. A lint rule flagging missing
   tenant scoping would be helpful by then (ADR-004 "Revisit").
8. **Over-engineering?** No — everything here is necessary for a working
   multi-tenant API. The permission classes are simpler than they could
   be, but that's because the full RBAC model is deferred to Milestone 6.
9. **Is tenant isolation guaranteed?** For the endpoints built this
   milestone (auth, tenant list/detail), yes — `TenantListView` is
   deliberately cross-tenant (shows all user's orgs); `CurrentTenantView`
   requires `HasActiveTenant` which checks request.tenant resolved via
   middleware. Tested by 8 tenant-isolation-specific tests.
10. **Are tests covering critical behavior?** Yes — 60 tests total (36 new);
    including register/login/logout/refresh flow, multi-tenant membership,
    cross-tenant data isolation, middleware resolution scenarios, and
    tenant-update authorization (owner-only). All passing against a real
    PostgreSQL instance.
