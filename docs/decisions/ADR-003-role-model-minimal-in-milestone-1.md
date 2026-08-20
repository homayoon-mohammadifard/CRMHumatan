# ADR-003: `Role` ships as a minimal lookup table in Milestone 1; full RBAC deferred to Milestone 6

## Status
Accepted (Milestone 1) — scheduled to be revisited in Milestone 6

## Context
Spec section 6 requires proper RBAC: `User -> Membership -> Tenant -> Role
-> Permissions`. Milestone 1 only asks for a "Membership foundation" — it
doesn't ask for the full permission matrix, and the domain models that
permissions would guard (Customer, Lead, Deal, Activity, Task) don't exist
yet.

## Decision
`Role` ships now as a minimal model: a fixed `slug` (owner, sales_manager,
sales_representative, support, viewer — matching spec section 49) + display
name + description. No `Permission` model, no `RolePermission` relation,
no OWN/TEAM/TENANT scope handling yet.

## Why
Building the full permission matrix before there's anything to
permission-check would be speculative and likely wrong — we don't yet know
the exact shape of `customers.view`-style permission strings needed once
Customer/Lead/Deal exist. Shipping the FK shape (`Membership.role ->
Role`) now avoids a painful later migration, without guessing at the
Permission model's design prematurely (spec section 40: "do not invent
requirements").

## Consequence
Until Milestone 6, `Role` is descriptive metadata only — it is not yet
enforced anywhere. No view should assume `Role` currently gates access.

## Revisit
Milestone 6 ("RBAC & Scoped Access") is where `Permission`,
`RolePermission`, and the OWN/TEAM/TENANT data-scope mechanism (spec
section 7) get designed and implemented, once Customer/Lead/Deal exist to
be scoped.
