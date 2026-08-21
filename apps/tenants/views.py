from __future__ import annotations

from rest_framework import generics, permissions
from rest_framework.request import Request
from rest_framework.response import Response

from apps.accounts.models import Membership
from apps.tenants.permissions import HasActiveTenant, IsTenantOwner
from apps.tenants.serializers import (
    TenantDetailSerializer,
    TenantMembershipListItemSerializer,
    TenantUpdateSerializer,
)


class TenantListView(generics.ListAPIView):
    """GET /api/v1/tenants/

    Lists every tenant the authenticated user has an active Membership
    in, with their role in each. Deliberately cross-tenant *by design*:
    this is the one endpoint whose whole purpose is "which of MY tenants
    can I access," scoped to the requesting user (not to any single
    active tenant) rather than via `.scoped()`/TenantOwnedModel.
    """

    serializer_class = TenantMembershipListItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Membership.objects.filter(user=self.request.user, is_active=True)
            .select_related("tenant", "role")
            .order_by("tenant__name")
        )


class CurrentTenantView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/v1/tenants/me/

    Operates on whatever tenant TenantResolutionMiddleware resolved from
    the X-Tenant-ID header for this request (spec section 45's "tenant
    resolution"). GET requires only an active tenant (HasActiveTenant);
    PATCH additionally requires the Owner role (IsTenantOwner) — the
    "basic authorization" spec section 45 asks this milestone to lay the
    foundation for.
    """

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated(), HasActiveTenant()]
        return [permissions.IsAuthenticated(), HasActiveTenant(), IsTenantOwner()]

    def get_serializer_class(self):
        if self.request.method in permissions.SAFE_METHODS:
            return TenantDetailSerializer
        return TenantUpdateSerializer

    def get_object(self):
        # request.tenant is set by TenantResolutionMiddleware and already
        # guaranteed non-None here by HasActiveTenant.
        return self.request.tenant

    def update(self, request: Request, *args, **kwargs) -> Response:
        response = super().update(request, *args, **kwargs)
        # Respond with the full read representation (not just the
        # writable subset) so the client sees the tenant's complete,
        # current state after a successful update.
        response.data = TenantDetailSerializer(self.get_object()).data
        return response
