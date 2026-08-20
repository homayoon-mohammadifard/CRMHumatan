"""
Tests for the core tenant-isolation primitives themselves: `tenant_context`
and `TenantScopedQuerySet` (`.for_tenant()` / `.scoped()`).

These are exercised against `Membership`, since it's the first real
`TenantOwnedModel` subclass that exists in Milestone 1. Customer/Lead/Deal
will get their own tenant-isolation tests in later milestones, but the
underlying mechanism is what's being verified here — see spec section 62,
the project's highest-priority test area.
"""

import pytest

from apps.accounts.models import Membership, User
from apps.core.context import get_current_tenant, tenant_context

pytestmark = pytest.mark.django_db


@pytest.fixture
def membership_a(tenant_a, owner_role):
    user = User.objects.create_user(email="owner@acme.test", password="x")
    return Membership.objects.create(user=user, tenant=tenant_a, role=owner_role)


@pytest.fixture
def membership_b(tenant_b, owner_role):
    user = User.objects.create_user(email="owner@globex.test", password="x")
    return Membership.objects.create(user=user, tenant=tenant_b, role=owner_role)


class TestTenantContext:
    def test_no_tenant_bound_by_default(self):
        assert get_current_tenant() is None

    def test_tenant_context_binds_and_restores(self, tenant_a):
        assert get_current_tenant() is None
        with tenant_context(tenant_a):
            assert get_current_tenant() == tenant_a
        assert get_current_tenant() is None

    def test_nested_tenant_context_restores_outer_value(self, tenant_a, tenant_b):
        with tenant_context(tenant_a):
            with tenant_context(tenant_b):
                assert get_current_tenant() == tenant_b
            assert get_current_tenant() == tenant_a
        assert get_current_tenant() is None


class TestTenantScopedQuerySetForTenant:
    """`.for_tenant()` — explicit, no ambient context required."""

    def test_for_tenant_returns_only_that_tenants_rows(
        self, tenant_a, tenant_b, membership_a, membership_b
    ):
        result = Membership.objects.for_tenant(tenant_a)

        assert list(result) == [membership_a]
        assert membership_b not in result

    def test_for_tenant_b_does_not_leak_tenant_a_rows(self, tenant_b, membership_a, membership_b):
        result = Membership.objects.for_tenant(tenant_b)

        assert list(result) == [membership_b]
        assert membership_a not in result


class TestTenantScopedQuerySetScoped:
    """`.scoped()` — uses ambient context set via `tenant_context`."""

    def test_scoped_without_context_raises(self):
        with pytest.raises(RuntimeError):
            list(Membership.objects.scoped())

    def test_scoped_with_context_filters_to_current_tenant(
        self, tenant_a, membership_a, membership_b
    ):
        with tenant_context(tenant_a):
            result = list(Membership.objects.scoped())

        assert result == [membership_a]

    def test_scoped_never_returns_other_tenants_rows(
        self, tenant_a, tenant_b, membership_a, membership_b
    ):
        with tenant_context(tenant_a):
            result_a = list(Membership.objects.scoped())
        with tenant_context(tenant_b):
            result_b = list(Membership.objects.scoped())

        assert membership_b not in result_a
        assert membership_a not in result_b

    def test_unscoped_manager_still_returns_all_tenants(self, membership_a, membership_b):
        # Sanity check documenting the deliberate design choice: the bare
        # manager is NOT auto-filtered. Call sites MUST opt in via
        # `.scoped()` or `.for_tenant()`.
        assert Membership.objects.count() == 2
