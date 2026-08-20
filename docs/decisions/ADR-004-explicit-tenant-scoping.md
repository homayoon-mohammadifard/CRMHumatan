# ADR-004: Tenant isolation is explicit (`.for_tenant()` / `.scoped()`), never automatic

## Status
Accepted (Milestone 1)

## Context
Spec section 8 requires "Shared Database + Shared Schema + Tenant Foreign
Key isolation." Section 9 lists a long, explicit set of surfaces that must
never leak cross-tenant data — list, detail, update, delete, search,
filter, nested resources, reports, exports, bulk operations, background
tasks. Section 62 makes tenant-isolation the single highest-priority test
area in the whole project.

Two designs were considered for how tenant-owned querysets get filtered:

1. **Automatic**: override `get_queryset()` on the default manager so
   `Model.objects.all()` is silently filtered to whatever tenant is bound
   in the current context.
2. **Explicit**: the bare manager (`Model.objects`) stays unscoped; call
   sites must deliberately call `.scoped()` (uses ambient request context)
   or `.for_tenant(tenant)` (explicit tenant, for platform-level code).

## Decision
Explicit (option 2). `TenantScopedQuerySet.scoped()` raises `RuntimeError`
if no tenant context is bound — a missing tenant filter fails loudly, at
development/test time, rather than silently.

## Why
Automatic filtering is convenient but has a worse failure mode: if the
context is ever unset unexpectedly (a management command, a Celery task,
a bug in middleware ordering), `Model.objects.all()` would either return
*zero* rows (masking a bug as "no data") or, if the fallback is "no
tenant bound = return everything," leak all tenants' data — silently,
with no error, exactly the scenario spec section 9 is most worried about.

An explicit `.scoped()` that raises makes the unsafe state impossible to
reach unnoticed: either the call site got tenant-filtered data, or the
test/request crashed loudly. A code reviewer can also see, syntactically,
whether a given queryset call is tenant-scoped just by reading it, which
directly supports the tenant-isolation test suite spec section 62 asks
for (list/detail/update/delete/search/filter/nested — each call site is
visibly either `.scoped()`, `.for_tenant()`, or bare/unscoped).

## Trade-off
Every new view/selector/service that touches a `TenantOwnedModel` must
remember to call `.scoped()` or `.for_tenant()` — this is not enforced by
the type system, only by code review and the isolation test suite. This
is accepted as the safer failure mode; see "Revisit" below for how it
could be hardened further.

## Revisit if
A large surface area of call sites accumulates and manual review no longer
scales — at that point, consider a lint rule / custom Django check that
flags any `Model.objects.<queryset-method>` call on a `TenantOwnedModel`
subclass that isn't preceded by `.scoped()`/`.for_tenant()` in the same
expression.
