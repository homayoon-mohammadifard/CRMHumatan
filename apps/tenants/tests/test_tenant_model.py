import pytest
from django.db import IntegrityError, transaction

from apps.tenants.models import Tenant

pytestmark = pytest.mark.django_db


class TestTenantModel:
    def test_create_tenant_defaults_to_trialing_status(self):
        tenant = Tenant.objects.create(name="Acme Company", slug="acme-company")
        assert tenant.status == Tenant.Status.TRIALING

    def test_slug_must_be_unique(self):
        Tenant.objects.create(name="Acme Company", slug="acme")
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Tenant.objects.create(name="Acme Company 2", slug="acme")

    def test_str_returns_name(self):
        tenant = Tenant.objects.create(name="Acme Company", slug="acme-company-2")
        assert str(tenant) == "Acme Company"
