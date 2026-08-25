
from __future__ import annotations

from rest_framework.permissions import BasePermission

# Imported here rather than duplicated: Role is owned by accounts, but a
# tenants-app permission class checking a role slug is exactly the kind of
# RBAC concept that legitimately crosses the two apps.
from apps.accounts.models import Role


class HasActiveTenant(BasePermission):
    message = (
        "A valid X-Tenant-ID header is required, matching one of your active tenant memberships."
    )

    def has_permission(self, request, view) -> bool:
        return getattr(request, "tenant", None) is not None


class IsTenantOwner(BasePermission):


    message = "Only the tenant owner can perform this action."

    def has_permission(self, request, view) -> bool:
        membership = getattr(request, "membership", None)
        return membership is not None and membership.role.slug == Role.Slug.OWNER
