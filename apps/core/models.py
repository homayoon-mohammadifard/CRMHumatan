"""
Shared abstract base models for the whole project.

`TenantOwnedModel` is the centralized tenant-isolation primitive discussed
in the Milestone 1 architecture review: every tenant-owned domain model
(Customer, Lead, Deal, Activity, Task, ... — arriving in later milestones)
should inherit from it instead of each app re-declaring its own `tenant`
FK and re-implementing `.filter(tenant=...)` by hand in every selector.
"""

from __future__ import annotations

from django.db import models

from apps.core.context import get_current_tenant


class TimeStampedModel(models.Model):
    """Abstract base adding created_at/updated_at to any model."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TenantScopedQuerySet(models.QuerySet):
    """QuerySet with explicit, deliberate tenant-filtering methods.

    There is no "auto-magic" filtering on `.all()` — an unscoped query
    still returns every tenant's rows. This is intentional: a call site
    that forgets to scope should be visibly wrong (all tenants' data) and
    easy to catch in review/tests, rather than silently and unpredictably
    empty because some invisible context wasn't set. See ADR-004.
    """

    def for_tenant(self, tenant) -> TenantScopedQuerySet:
        """Explicit scoping to a given Tenant instance or ID.

        Use this for platform-level code that legitimately operates across
        or outside the current request's tenant (e.g. an admin action, a
        management command operating on a specific tenant).
        """
        return self.filter(tenant=tenant)

    def scoped(self) -> TenantScopedQuerySet:
        """Scope to the tenant bound in the current context (see
        apps.core.context). This is what views/selectors/serializers
        serving tenant-facing data should call.

        Raises RuntimeError if no tenant context is active, so a missing
        tenant filter fails loudly at development/test time instead of
        silently leaking cross-tenant data in production.
        """
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
    """Abstract base for every model that belongs to exactly one Tenant.

    `related_name="%(class)ss"` gives each subclass its own reverse
    accessor on Tenant (e.g. `tenant.memberships`, and later
    `tenant.customers`, `tenant.leads`, ...) without manual repetition.
    """

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="%(class)ss",
    )

    objects = TenantScopedManager()

    class Meta:
        abstract = True
