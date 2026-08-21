import pytest

pytestmark = pytest.mark.django_db


class TestTenantResolutionMiddleware:
    """Tests for the tenant resolution mechanism (spec section 45 /
    Milestone 2). The middleware is invoked by Django's request pipeline
    before views run, so these are tested indirectly via API endpoints
    that set request.tenant/request.membership, which the endpoints then
    check with HasActiveTenant / IsTenantOwner permissions.
    """

    def test_tenant_context_is_set_for_valid_membership(
        self, api_client, make_user, tenant_a, owner_role, make_membership
    ):
        user = make_user(email="user@example.test")
        make_membership(user=user, tenant=tenant_a, role=owner_role)

        login_response = api_client.post(
            "/api/v1/auth/login/",
            {"email": "user@example.test", "password": "S3curePass!123"},
            format="json",
        )
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")

        # The /tenants/me/ endpoint requires HasActiveTenant permission,
        # which will fail if request.tenant is None. Success means the
        # middleware correctly resolved and set request.tenant.
        response = api_client.get("/api/v1/tenants/me/", HTTP_X_TENANT_ID=str(tenant_a.id))

        assert response.status_code == 200
        assert response.data["id"] == tenant_a.id

    def test_missing_x_tenant_id_header_leaves_tenant_unresolved(
        self, authed_client
    ):
        client, _user = authed_client

        # No X-Tenant-ID header means request.tenant remains None, so
        # HasActiveTenant rejects with 403 Forbidden (permission denied).
        response = client.get("/api/v1/tenants/me/")

        assert response.status_code == 403

    def test_invalid_tenant_id_leaves_tenant_unresolved(
        self, authed_client
    ):
        client, _user = authed_client

        # Non-numeric tenant ID.
        response = client.get(
            "/api/v1/tenants/me/", HTTP_X_TENANT_ID="not-a-number"
        )

        assert response.status_code == 403

    def test_tenant_mismatch_leaves_tenant_unresolved(
        self, api_client, make_user, tenant_a, tenant_b, owner_role, make_membership
    ):
        user_a = make_user(email="user-a@example.test")
        make_membership(user=user_a, tenant=tenant_a, role=owner_role)
        # User is NOT a member of Tenant B.

        login_response = api_client.post(
            "/api/v1/auth/login/",
            {"email": "user-a@example.test", "password": "S3curePass!123"},
            format="json",
        )
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")

        # Trying to access Tenant B should fail with 403 (permission denied).
        response = api_client.get(
            "/api/v1/tenants/me/", HTTP_X_TENANT_ID=str(tenant_b.id)
        )

        assert response.status_code == 403

    def test_inactive_membership_leaves_tenant_unresolved(
        self, api_client, make_user, tenant_a, owner_role, make_membership
    ):
        user = make_user(email="user@example.test")
        membership = make_membership(user=user, tenant=tenant_a, role=owner_role)
        membership.is_active = False
        membership.save()

        login_response = api_client.post(
            "/api/v1/auth/login/",
            {"email": "user@example.test", "password": "S3curePass!123"},
            format="json",
        )
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")

        response = api_client.get(
            "/api/v1/tenants/me/", HTTP_X_TENANT_ID=str(tenant_a.id)
        )

        assert response.status_code == 403

    def test_unauthenticated_request_leaves_tenant_unresolved(
        self, api_client, tenant_a
    ):
        # No authentication means the JWT decode fails, so request.tenant
        # and request.membership are both None.
        response = api_client.get(
            "/api/v1/tenants/me/", HTTP_X_TENANT_ID=str(tenant_a.id)
        )

        assert response.status_code == 401
