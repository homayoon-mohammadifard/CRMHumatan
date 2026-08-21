import pytest

from apps.accounts.models import Membership, Role, User
from apps.tenants.models import Tenant

pytestmark = pytest.mark.django_db


class TestRegisterView:
    def test_register_creates_user_tenant_and_owner_membership(self, api_client):
        response = api_client.post(
            "/api/v1/auth/register/",
            {
                "email": "ali@acme.test",
                "password": "S3curePass!123",
                "first_name": "Ali",
                "last_name": "Ahmadi",
                "tenant_name": "Acme Company",
            },
            format="json",
        )

        assert response.status_code == 201, response.data
        user = User.objects.get(email="ali@acme.test")
        assert user.first_name == "Ali"
        assert user.check_password("S3curePass!123")

        tenant = Tenant.objects.get(name="Acme Company")
        membership = Membership.objects.get(user=user, tenant=tenant)
        assert membership.role.slug == Role.Slug.OWNER

    def test_register_response_includes_membership(self, api_client):
        response = api_client.post(
            "/api/v1/auth/register/",
            {
                "email": "b@acme.test",
                "password": "S3curePass!123",
                "tenant_name": "B Co",
            },
            format="json",
        )

        assert response.status_code == 201
        assert response.data["memberships"][0]["role"] == "owner"
        assert response.data["memberships"][0]["tenant_name"] == "B Co"

    def test_register_rejects_duplicate_email(self, api_client, make_user):
        make_user(email="dup@example.test")

        response = api_client.post(
            "/api/v1/auth/register/",
            {
                "email": "dup@example.test",
                "password": "S3curePass!123",
                "tenant_name": "Some Co",
            },
            format="json",
        )

        assert response.status_code == 400
        assert "email" in response.data["errors"]

    def test_register_rejects_weak_password(self, api_client):
        response = api_client.post(
            "/api/v1/auth/register/",
            {
                "email": "weak@example.test",
                "password": "12345678",
                "tenant_name": "Some Co",
            },
            format="json",
        )

        assert response.status_code == 400
        assert "password" in response.data["errors"]

    def test_register_does_not_leave_partial_state_on_duplicate_slug_race(self, api_client):
        # Two companies with the same name should not collide -- the slug
        # generator must dedupe rather than fail the whole registration.
        api_client.post(
            "/api/v1/auth/register/",
            {
                "email": "first@acme.test",
                "password": "S3curePass!123",
                "tenant_name": "Acme",
            },
            format="json",
        )
        response = api_client.post(
            "/api/v1/auth/register/",
            {
                "email": "second@acme.test",
                "password": "S3curePass!123",
                "tenant_name": "Acme",
            },
            format="json",
        )

        assert response.status_code == 201
        slugs = set(Tenant.objects.filter(name="Acme").values_list("slug", flat=True))
        assert slugs == {"acme", "acme-2"}

    def test_error_response_shape_is_normalized(self, api_client):
        response = api_client.post(
            "/api/v1/auth/register/",
            {"email": "not-an-email", "password": "x", "tenant_name": ""},
            format="json",
        )

        assert response.status_code == 400
        assert set(response.data.keys()) == {"detail", "code", "errors"}
