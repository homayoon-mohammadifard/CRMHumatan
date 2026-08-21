from __future__ import annotations

from rest_framework import serializers

from apps.tenants.models import Tenant


class TenantMembershipListItemSerializer(serializers.Serializer):
    """One row of GET /api/v1/tenants/ — a tenant the current user belongs
    to, plus their role in it. Backed by a Membership queryset annotated
    in the view, not a ModelSerializer on Tenant, since the interesting
    per-row data (the user's role) lives on Membership, not Tenant.
    """

    id = serializers.IntegerField(source="tenant.id")
    name = serializers.CharField(source="tenant.name")
    slug = serializers.CharField(source="tenant.slug")
    status = serializers.CharField(source="tenant.status")
    role = serializers.CharField(source="role.slug")
    role_name = serializers.CharField(source="role.name")


class TenantDetailSerializer(serializers.ModelSerializer):
    """GET /api/v1/tenants/me/ — the currently active tenant (resolved via
    X-Tenant-ID). Read-only fields only; see TenantUpdateSerializer for
    the writable subset.
    """

    class Meta:
        model = Tenant
        fields = ["id", "name", "slug", "status", "created_at", "updated_at"]
        read_only_fields = fields


class TenantUpdateSerializer(serializers.ModelSerializer):
    """PATCH /api/v1/tenants/me/ — owner-only (see
    apps.tenants.permissions.IsTenantOwner). Deliberately excludes
    `status`: status transitions (suspended/cancelled/...) are a
    platform-level concern, not something a tenant owner can set on
    themselves, and are out of scope until explicitly requested.
    """

    class Meta:
        model = Tenant
        fields = ["name"]
