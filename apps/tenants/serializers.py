from __future__ import annotations

from rest_framework import serializers

from apps.tenants.models import Tenant


class TenantMembershipListItemSerializer(serializers.Serializer):
    id = serializers.IntegerField(source="tenant.id")
    name = serializers.CharField(source="tenant.name")
    slug = serializers.CharField(source="tenant.slug")
    status = serializers.CharField(source="tenant.status")
    role = serializers.CharField(source="role.slug")
    role_name = serializers.CharField(source="role.name")


class TenantDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tenant
        fields = ["id", "name", "slug", "status", "created_at", "updated_at"]
        read_only_fields = fields


class TenantUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tenant
        fields = ["name"]
