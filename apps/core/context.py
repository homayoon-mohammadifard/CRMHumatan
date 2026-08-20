"""
Request-scoped "current tenant" context.

This is the low-level primitive that the tenant-isolation architecture is
built on (see docs/decisions/ADR-004). It does NOT resolve a tenant from a
request — that is TenantResolutionMiddleware's job, arriving in Milestone 2
once authentication exists. Milestone 1 only ships this primitive plus the
abstract base models that will consume it, so the shape doesn't need to
change once real request handling lands.

Implemented with `contextvars` (not a plain thread-local) so it behaves
correctly under async views/ASGI as well as sync/WSGI.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.tenants.models import Tenant

_current_tenant: ContextVar[Tenant | None] = ContextVar("current_tenant", default=None)


def get_current_tenant() -> Tenant | None:
    """Return the Tenant bound to the current context, or None if unset."""
    return _current_tenant.get()


def set_current_tenant(tenant: Tenant | None) -> None:
    """
    Bind a Tenant to the current context.

    Prefer the `tenant_context` context manager over calling this directly,
    so the previous value is always restored deterministically.
    """
    _current_tenant.set(tenant)


@contextmanager
def tenant_context(tenant: Tenant | None):
    """
    Temporarily bind `tenant` as the current tenant for the duration of the
    `with` block (e.g. a request, a management command, a background job).

    Usage:
        with tenant_context(some_tenant):
            Customer.objects.scoped()  # filtered to some_tenant
    """
    token = _current_tenant.set(tenant)
    try:
        yield
    finally:
        _current_tenant.reset(token)
