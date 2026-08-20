# ADR-002: Platform superuser (`is_staff`/`is_superuser`) is separate from Tenant RBAC

## Status
Accepted (Milestone 1)

## Context
Django ships `is_staff`/`is_superuser` on the user model for Django-admin
access. Spec sections 5A and 6 draw a hard line: platform-level access must
never be conflated with a Tenant's business permissions.

## Decision
`is_staff`/`is_superuser` control Django admin / platform-operator access
only. They are never checked in business-domain authorization logic
(`customers.view`, `deals.update`, etc., arriving in later milestones).
All tenant-facing authorization goes through Membership -> Role (and later
Role -> Permission).

## Why
`if user.is_superuser: allow_everything()` is a common but dangerous
shortcut — spec section 6 explicitly forbids relying on it for business
authorization, and section 40 lists it under "what not to do." A platform
engineer with Django-admin access should not automatically be treated as
having business permissions inside every tenant's CRM data; those are
different concerns (operating the platform vs. operating a business).

## Consequence
Debugging/support tooling that needs a platform operator to act "as" a
tenant user must do so explicitly (e.g. an audited impersonation flow),
not implicitly via `is_superuser` bypassing RBAC checks. That flow is out
of scope until explicitly requested.
