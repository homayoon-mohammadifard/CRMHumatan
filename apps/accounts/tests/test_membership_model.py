import pytest
from django.db import IntegrityError, transaction

from apps.accounts.models import Membership, User

pytestmark = pytest.mark.django_db


class TestMembershipUniqueness:
    def test_one_membership_per_user_per_tenant_allowed(self, tenant_a, owner_role):
        user = User.objects.create_user(email="owner@acme.test", password="x")
        membership = Membership.objects.create(user=user, tenant=tenant_a, role=owner_role)

        assert membership.pk is not None
        assert membership.tenant_id == tenant_a.id
        assert membership.role_id == owner_role.id

    def test_duplicate_membership_for_same_user_and_tenant_is_rejected(
        self, tenant_a, owner_role, sales_rep_role
    ):
        user = User.objects.create_user(email="dup@acme.test", password="x")
        Membership.objects.create(user=user, tenant=tenant_a, role=owner_role)

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Membership.objects.create(user=user, tenant=tenant_a, role=sales_rep_role)

    def test_same_user_can_have_memberships_in_different_tenants(
        self, tenant_a, tenant_b, owner_role, sales_rep_role
    ):
        user = User.objects.create_user(email="multi@example.test", password="x")

        membership_a = Membership.objects.create(user=user, tenant=tenant_a, role=owner_role)
        membership_b = Membership.objects.create(user=user, tenant=tenant_b, role=sales_rep_role)

        assert user.memberships.count() == 2
        assert membership_a.tenant_id != membership_b.tenant_id
        assert membership_a.role_id != membership_b.role_id


class TestMembershipTenantScoping:
    def test_for_tenant_only_returns_that_tenants_memberships(self, tenant_a, tenant_b, owner_role):
        user_a = User.objects.create_user(email="a@acme.test", password="x")
        user_b = User.objects.create_user(email="b@globex.test", password="x")
        Membership.objects.create(user=user_a, tenant=tenant_a, role=owner_role)
        Membership.objects.create(user=user_b, tenant=tenant_b, role=owner_role)

        tenant_a_memberships = Membership.objects.for_tenant(tenant_a)

        assert tenant_a_memberships.count() == 1
        assert tenant_a_memberships.first().user_id == user_a.id
