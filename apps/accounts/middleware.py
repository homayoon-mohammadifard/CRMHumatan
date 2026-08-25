from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from apps.core.context import tenant_context

TENANT_HEADER = "X-Tenant-ID"


class TenantResolutionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self._jwt_authenticator = JWTAuthentication()

    def __call__(self, request: HttpRequest) -> HttpResponse:
        tenant, membership = self._resolve(request)
        request.tenant = tenant
        request.membership = membership

        if tenant is not None:
            with tenant_context(tenant):
                return self.get_response(request)
        return self.get_response(request)

    def _resolve(self, request: HttpRequest):
        from apps.accounts.models import Membership

        tenant_id = request.headers.get(TENANT_HEADER)
        if not tenant_id:
            return None, None

        try:
            auth_result = self._jwt_authenticator.authenticate(request)
        except (InvalidToken, TokenError):
            return None, None

        if auth_result is None:
            return None, None
        user, _validated_token = auth_result

        if not tenant_id.isdigit():
            return None, None

        membership = (
            Membership.objects.filter(user=user, tenant_id=tenant_id, is_active=True)
            .select_related("tenant", "role")
            .first()
        )
        if membership is None:
            return None, None

        return membership.tenant, membership
