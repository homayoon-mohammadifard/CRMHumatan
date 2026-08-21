from __future__ import annotations

from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.accounts.serializers import (
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
    UserSerializer,
)


class RegisterView(generics.CreateAPIView):
    """POST /api/v1/auth/register/

    Signs up a brand-new company: creates a User, a new Tenant, and an
    owner Membership linking them (spec sections 5B, 13, 20). Publicly
    accessible — this is how a new tenant comes into existence in the
    first place, so it cannot require authentication.
    """

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request: Request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    """POST /api/v1/auth/login/

    Standard email+password -> JWT access/refresh pair, via
    CustomTokenObtainPairSerializer (also returns identity + tenant
    memberships so the client can pick an active tenant next).
    """

    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]


class LogoutView(APIView):
    """POST /api/v1/auth/logout/

    Blacklists the given refresh token so it can no longer be used to
    obtain new access tokens (relies on SIMPLE_JWT's
    BLACKLIST_AFTER_ROTATION / the token_blacklist app — see
    config/settings/base.py). This does not invalidate any access token
    already issued; those simply expire on their own short lifetime
    (ACCESS_TOKEN_LIFETIME_MINUTES).
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request: Request) -> Response:
        refresh = request.data.get("refresh")
        if not refresh:
            raise ValidationError({"refresh": ["This field is required."]})
        try:
            RefreshToken(refresh).blacklist()
        except TokenError as exc:
            raise ValidationError({"refresh": [str(exc)]}) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveAPIView):
    """GET /api/v1/auth/me/

    The authenticated user's own identity and the full list of tenants
    they hold a Membership in (spec section 4 — a user may belong to more
    than one Tenant). Deliberately NOT tenant-scoped: this reflects the
    user's global identity, independent of whichever tenant (if any) is
    currently selected via X-Tenant-ID.
    """

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
