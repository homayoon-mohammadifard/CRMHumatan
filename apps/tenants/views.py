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

    serializer_class = TenantMembershipListItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Membership.objects.filter(user=self.request.user, is_active=True)
            .select_related("tenant", "role")
            .order_by("tenant__name")
        )


class CurrentTenantView(generics.RetrieveUpdateAPIView):

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated(), HasActiveTenant()]
        return [permissions.IsAuthenticated(), HasActiveTenant(), IsTenantOwner()]

    def get_serializer_class(self):
        if self.request.method in permissions.SAFE_METHODS:
            return TenantDetailSerializer
        return TenantUpdateSerializer

    def get_object(self):
        return self.request.tenant

    def update(self, request: Request, *args, **kwargs) -> Response:
        response = super().update(request, *args, **kwargs)

        response.data = TenantDetailSerializer(self.get_object()).data
        return response
