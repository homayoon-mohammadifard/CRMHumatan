import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Membership, Role, User
from apps.tenants.models import Tenant


@pytest.fixture
def tenant_a(db):
    return Tenant.objects.create(name="Acme Company", slug="acme-company")


@pytest.fixture
def tenant_b(db):
    return Tenant.objects.create(name="Globex Corp", slug="globex-corp")


@pytest.fixture
def owner_role(db):
    return Role.objects.get_or_create(slug=Role.Slug.OWNER, defaults={"name": "Owner"})[0]


@pytest.fixture
def sales_rep_role(db):
    return Role.objects.get_or_create(
        slug=Role.Slug.SALES_REPRESENTATIVE,
        defaults={"name": "Sales Representative"},
    )[0]


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def make_user(db):
    def _make_user(email="user@example.test", password="S3curePass!123", **kwargs):
        return User.objects.create_user(email=email, password=password, **kwargs)

    return _make_user


@pytest.fixture
def make_membership(db):
    def _make_membership(*, user, tenant, role):
        return Membership.objects.create(user=user, tenant=tenant, role=role)

    return _make_membership


@pytest.fixture
def authed_client(api_client, make_user):
    """An APIClient authenticated (via a real login call) as a fresh user
    with no tenant membership yet."""
    user = make_user(email="plain-user@example.test")
    response = api_client.post(
        "/api/v1/auth/login/",
        {"email": "plain-user@example.test", "password": "S3curePass!123"},
        format="json",
    )
    assert response.status_code == 200, response.data
    access = response.data["access"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return api_client, user
