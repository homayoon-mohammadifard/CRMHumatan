

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
    _current_tenant.set(tenant)


@contextmanager
def tenant_context(tenant: Tenant | None):

    token = _current_tenant.set(tenant)
    try:
        yield
    finally:
        _current_tenant.reset(token)
