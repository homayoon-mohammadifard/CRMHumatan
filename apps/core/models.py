
from __future__ import annotations

from django.db import models

from apps.core.context import get_current_tenant


class TimeStampedModel(models.Model):

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TenantScopedQuerySet(models.QuerySet):

    def for_tenant(self, tenant) -> TenantScopedQuerySet:
        return self.filter(tenant=tenant)

    def scoped(self) -> TenantScopedQuerySet:

        tenant = get_current_tenant()
        if tenant is None:
            raise RuntimeError(
                "No tenant is bound in the current context. Use "
                "`.for_tenant(tenant)` for explicit platform-level access, "
                "or ensure tenant context is set (via TenantResolutionMiddleware "
                "or `tenant_context(...)`) before calling `.scoped()`."
            )
        return self.filter(tenant=tenant)


class TenantScopedManager(models.Manager.from_queryset(TenantScopedQuerySet)):
    """Default manager for tenant-owned models. See TenantScopedQuerySet."""


class TenantOwnedModel(TimeStampedModel):

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="%(class)ss",
    )

    objects = TenantScopedManager()

    class Meta:
        abstract = True
