import pytest

from apps.accounts.models import Role
from apps.tenants.models import Tenant


@pytest.fixture
def tenant_a(db):
    return Tenant.objects.create(name="Acme Company", slug="acme-company")


@pytest.fixture
def tenant_b(db):
    return Tenant.objects.create(name="Globex Corp", slug="globex-corp")


@pytest.fixture
def owner_role(db):
    return Role.objects.create(slug=Role.Slug.OWNER, name="Owner")


@pytest.fixture
def sales_rep_role(db):
    return Role.objects.create(slug=Role.Slug.SALES_REPRESENTATIVE, name="Sales Representative")
