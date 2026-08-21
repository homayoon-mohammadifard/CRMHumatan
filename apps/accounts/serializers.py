from __future__ import annotations

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import Membership, User
from apps.accounts.services import register_user_and_tenant


class MembershipSummarySerializer(serializers.ModelSerializer):
    """A user's membership in one tenant, from the user's point of view —
    used in /auth/me/ and the login response so the client can present
    "which of your organizations do you want to work in" without a
    separate round-trip.
    """

    tenant_id = serializers.IntegerField(source="tenant.id")
    tenant_name = serializers.CharField(source="tenant.name")
    tenant_slug = serializers.CharField(source="tenant.slug")
    role = serializers.CharField(source="role.slug")
    role_name = serializers.CharField(source="role.name")

    class Meta:
        model = Membership
        fields = [
            "tenant_id",
            "tenant_name",
            "tenant_slug",
            "role",
            "role_name",
            "is_active",
        ]


class UserSerializer(serializers.ModelSerializer):
    memberships = MembershipSummarySerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "memberships",
        ]
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer):
    """Signup for a brand-new company: creates a User, a new Tenant, and
    an owner Membership linking them. See
    apps.accounts.services.register_user_and_tenant.
    """

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    first_name = serializers.CharField(required=False, allow_blank=True, default="")
    last_name = serializers.CharField(required=False, allow_blank=True, default="")
    tenant_name = serializers.CharField(max_length=200)

    def validate_email(self, value: str) -> str:
        normalized = User.objects.normalize_email(value)
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return normalized

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    def create(self, validated_data):
        result = register_user_and_tenant(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            tenant_name=validated_data["tenant_name"],
        )
        return result.user

    def update(self, instance, validated_data):
        raise NotImplementedError("RegisterSerializer does not support update().")


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Standard SimpleJWT login, with the user's identity and tenant
    memberships attached to the response — the frontend needs this
    immediately after login to know which tenant(s) to offer as "active"
    (see apps.accounts.middleware.TenantResolutionMiddleware for how an
    active tenant is then selected via the X-Tenant-ID header).

    The JWT payload itself intentionally carries no tenant claim — see
    the module docstring on TenantResolutionMiddleware for why.
    """

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data
