"""Permission classes for tenant-facing endpoints.

These live here (not in apps.accounts) because they gate access to
*tenant* views, even though the underlying fact they check (Role) is
owned by the accounts app — RBAC inherently straddles both. See
ARCHITECTURE.md for the full identity/tenant model.

Full RBAC (Permission model, OWN/TEAM/TENANT scopes) is deferred to
Milestone 6 (ADR-003) — these are the "basic authorization" primitives
spec section 45 asks for as this milestone's foundation, not the final
permission system.
"""

from __future__ import annotations

from rest_framework.permissions import BasePermission

# Imported here rather than duplicated: Role is owned by accounts, but a
# tenants-app permission class checking a role slug is exactly the kind of
# RBAC concept that legitimately crosses the two apps.
from apps.accounts.models import Role


class HasActiveTenant(BasePermission):
    """Requires that TenantResolutionMiddleware successfully resolved an
    active tenant for this request (i.e. a valid `X-Tenant-ID` header
    matching one of the authenticated user's active Memberships).
    """

    message = (
        "A valid X-Tenant-ID header is required, matching one of your active tenant memberships."
    )

    def has_permission(self, request, view) -> bool:
        return getattr(request, "tenant", None) is not None


class IsTenantOwner(BasePermission):
    """Requires HasActiveTenant AND that the resolved Membership's role is
    Owner. Used for tenant-settings-changing operations (spec sections 6
    and 45's "basic authorization").
    """

    message = "Only the tenant owner can perform this action."

    def has_permission(self, request, view) -> bool:
        membership = getattr(request, "membership", None)
        return membership is not None and membership.role.slug == Role.Slug.OWNER
