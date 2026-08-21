"""
Tenant resolution middleware (spec section 45 — "Milestone 2: Tenant
Resolution").

Design (see ARCHITECTURE.md "Tenant context" and ADR-004): the JWT itself
carries only user identity, not a tenant claim — a user can hold Memberships
in more than one Tenant (spec section 4), and baking a single tenant into
the token would force a re-login/re-issue every time the user switches
organizations. Instead, the client sends the *desired* active tenant on
each request via the `X-Tenant-ID` header, and this middleware
cross-validates it against the authenticated user's real Membership rows
before trusting it for anything.

This directly implements spec section 8's requirement: "NEVER trust
client-supplied tenant IDs for authorization... Tenant context should be
derived from authenticated identity and membership/session/request
context." The header is only ever a *hint* about which of the user's own
tenants they want active — it is never used to authorize access to a
tenant the user isn't actually a member of.

If resolution succeeds, the resolved Tenant is bound via
`apps.core.context.tenant_context` for the duration of the request, so any
code that calls `Model.objects.scoped()` during that request is
automatically scoped to it.

This is implemented as a plain Django middleware (not a DRF
authentication/permission class) because DRF's request-scoped
`request.user` is only populated lazily during view dispatch. To resolve a
tenant this early, the middleware authenticates the JWT itself using the
same `JWTAuthentication` class DRF would use — this is a few extra
microseconds of redundant token validation per request, traded for the
tenant being resolved (and hence `.scoped()` usable) before the view body
even runs.
"""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from apps.core.context import tenant_context

TENANT_HEADER = "X-Tenant-ID"


class TenantResolutionMiddleware:
    """Resolves `request.tenant` / `request.membership` from the
    `X-Tenant-ID` header, cross-validated against the authenticated user's
    Membership rows. Both are `None` when no tenant is resolved (e.g. the
    request is unauthenticated, has no header, or requests a tenant the
    user doesn't belong to) — views/permissions that require an active
    tenant must check for `None` explicitly (see
    `apps.tenants.permissions.HasActiveTenant`).
    """

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
        # Local import: Membership lives in this same app (accounts), but
        # kept as a local import to make the module importable even before
        # migrations run (e.g. during `manage.py check` at import time).
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
            # Malformed header value (not a valid PK) — treat the same as
            # "no tenant resolved" rather than letting a DB-level error
            # surface as a 500.
            return None, None

        membership = (
            Membership.objects.filter(user=user, tenant_id=tenant_id, is_active=True)
            .select_related("tenant", "role")
            .first()
        )
        if membership is None:
            return None, None

        return membership.tenant, membership
