# ADR-001: Tenant ownership is derived from Membership, not a `Tenant.owner` FK

## Status
Accepted (Milestone 1)

## Context
Spec section 5B describes a "Tenant Owner" — the person who owns/manages a
company's Humatan CRM account. A tempting shortcut is a direct
`Tenant.owner = ForeignKey(User)` field.

## Decision
`Tenant` has no `owner` field. Ownership is represented purely as a
`Membership` row with `role.slug == Role.Slug.OWNER` for that tenant.

## Why
A separate `owner` FK duplicates a fact that `Membership` already
represents. Two sources of truth for "who owns this tenant" can drift:
e.g. an owner Membership is deactivated or transferred, but nobody updates
the `owner` FK to match. Deriving ownership from Membership means there is
exactly one place this fact can be wrong.

## Trade-off
Looking up "the owner(s) of tenant X" requires a query
(`Membership.objects.for_tenant(x).filter(role__slug=Role.Slug.OWNER)`)
rather than a direct FK dereference. This is a selector-layer concern and
is cheap with the `(tenant, role)` index already defined on `Membership`.

## Revisit if
Product requirements introduce a concept of tenant ownership that is NOT
1:1 with holding the Owner role (e.g. billing-contact-only ownership
distinct from operational admin access).
