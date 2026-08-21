import pytest

pytestmark = pytest.mark.django_db


class TestTenantListView:
    def test_tenant_list_requires_authentication(self, api_client):
        response = api_client.get("/api/v1/tenants/")
        assert response.status_code == 401

    def test_tenant_list_returns_user_memberships_with_roles(
        self, authed_client, tenant_a, tenant_b, owner_role, sales_rep_role, make_membership
    ):
        client, user = authed_client
        make_membership(user=user, tenant=tenant_a, role=owner_role)
        make_membership(user=user, tenant=tenant_b, role=sales_rep_role)

        response = client.get("/api/v1/tenants/")

        assert response.status_code == 200
        assert len(response.data["results"]) == 2
        tenant_ids = [t["id"] for t in response.data["results"]]
        assert tenant_a.id in tenant_ids
        assert tenant_b.id in tenant_ids
        # One is owner, one is sales_rep
        roles = [t["role"] for t in response.data["results"]]
        assert "owner" in roles
        assert "sales_representative" in roles

    def test_tenant_list_excludes_inactive_memberships(
        self, authed_client, tenant_a, owner_role, make_membership
    ):
        client, user = authed_client
        membership = make_membership(user=user, tenant=tenant_a, role=owner_role)
        membership.is_active = False
        membership.save()

        response = client.get("/api/v1/tenants/")

        assert response.status_code == 200
        assert len(response.data["results"]) == 0

    def test_tenant_list_is_cross_tenant_by_design(
        self, api_client, make_user, tenant_a, tenant_b, owner_role, make_membership
    ):
        # User A belongs to Tenant A only.
        user_a = make_user(email="user-a@example.test")
        make_membership(user=user_a, tenant=tenant_a, role=owner_role)

        # User B belongs to Tenant B only.
        user_b = make_user(email="user-b@example.test")
        make_membership(user=user_b, tenant=tenant_b, role=owner_role)

        # User A logs in and lists tenants.
        api_client.post(
            "/api/v1/auth/login/",
            {"email": "user-a@example.test", "password": "S3curePass!123"},
            format="json",
        )
        login_response = api_client.post(
            "/api/v1/auth/login/",
            {"email": "user-a@example.test", "password": "S3curePass!123"},
            format="json",
        )
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")

        response = api_client.get("/api/v1/tenants/")

        # User A sees only Tenant A, not Tenant B.
        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["id"] == tenant_a.id


class TestCurrentTenantView:
    def test_current_tenant_requires_x_tenant_id_header(self, authed_client):
        client, _user = authed_client

        response = client.get("/api/v1/tenants/me/")

        assert response.status_code == 403
        assert "X-Tenant-ID" in response.data.get("detail", "")

    def test_current_tenant_requires_valid_membership(
        self, authed_client, tenant_a, make_user, tenant_b, owner_role, make_membership
    ):
        client, user = authed_client
        # User is a member of Tenant A.
        make_membership(user=user, tenant=tenant_a, role=owner_role)

        # Requesting Tenant B (which they're not a member of) should fail.
        response = client.get("/api/v1/tenants/me/", HTTP_X_TENANT_ID=str(tenant_b.id))

        assert response.status_code == 403

    def test_current_tenant_get_returns_tenant_details(
        self, authed_client, tenant_a, owner_role, make_membership
    ):
        client, user = authed_client
        make_membership(user=user, tenant=tenant_a, role=owner_role)

        response = client.get("/api/v1/tenants/me/", HTTP_X_TENANT_ID=str(tenant_a.id))

        assert response.status_code == 200
        assert response.data["id"] == tenant_a.id
        assert response.data["name"] == tenant_a.name
        assert response.data["slug"] == tenant_a.slug

    def test_current_tenant_patch_requires_owner_role(
        self, authed_client, tenant_a, sales_rep_role, make_membership
    ):
        client, user = authed_client
        make_membership(user=user, tenant=tenant_a, role=sales_rep_role)

        response = client.patch(
            "/api/v1/tenants/me/",
            {"name": "New Name"},
            format="json",
            HTTP_X_TENANT_ID=str(tenant_a.id),
        )

        assert response.status_code == 403

    def test_current_tenant_patch_allows_owner_to_update_name(
        self, authed_client, tenant_a, owner_role, make_membership
    ):
        client, user = authed_client
        make_membership(user=user, tenant=tenant_a, role=owner_role)

        response = client.patch(
            "/api/v1/tenants/me/",
            {"name": "Acme Inc."},
            format="json",
            HTTP_X_TENANT_ID=str(tenant_a.id),
        )

        assert response.status_code == 200
        assert response.data["name"] == "Acme Inc."

        # Verify the database was updated.
        tenant_a.refresh_from_db()
        assert tenant_a.name == "Acme Inc."

    def test_current_tenant_patch_does_not_allow_changing_slug(
        self, authed_client, tenant_a, owner_role, make_membership
    ):
        client, user = authed_client
        make_membership(user=user, tenant=tenant_a, role=owner_role)

        response = client.patch(
            "/api/v1/tenants/me/",
            {"slug": "acme-inc"},
            format="json",
            HTTP_X_TENANT_ID=str(tenant_a.id),
        )

        # slug is read-only, so the request succeeds but slug doesn't change.
        assert response.status_code == 200
        tenant_a.refresh_from_db()
        assert tenant_a.slug == "acme-company"


class TestTenantIsolation:
    """High-priority tests (spec section 62) ensuring cross-tenant data
    leaks are impossible via tenant endpoints."""

    def test_list_does_not_expose_other_users_tenants(
        self, api_client, make_user, tenant_a, tenant_b, owner_role, make_membership
    ):
        user_a = make_user(email="user-a@example.test")
        user_b = make_user(email="user-b@example.test")
        make_membership(user=user_a, tenant=tenant_a, role=owner_role)
        make_membership(user=user_b, tenant=tenant_b, role=owner_role)

        # User A logs in and lists.
        login_response = api_client.post(
            "/api/v1/auth/login/",
            {"email": "user-a@example.test", "password": "S3curePass!123"},
            format="json",
        )
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")

        response = api_client.get("/api/v1/tenants/")

        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["id"] == tenant_a.id
        assert response.data["results"][0]["id"] != tenant_b.id

    def test_detail_prevents_access_to_other_tenants(
        self, api_client, make_user, tenant_a, tenant_b, owner_role, make_membership
    ):
        user_a = make_user(email="user-a@example.test")
        make_membership(user=user_a, tenant=tenant_a, role=owner_role)

        login_response = api_client.post(
            "/api/v1/auth/login/",
            {"email": "user-a@example.test", "password": "S3curePass!123"},
            format="json",
        )
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")

        # User A tries to access Tenant B via X-Tenant-ID.
        response = api_client.get("/api/v1/tenants/me/", HTTP_X_TENANT_ID=str(tenant_b.id))

        assert response.status_code == 403

    def test_update_prevents_modification_of_other_tenants(
        self, api_client, make_user, tenant_a, tenant_b, owner_role, make_membership
    ):
        user_a = make_user(email="user-a@example.test")
        make_membership(user=user_a, tenant=tenant_a, role=owner_role)

        login_response = api_client.post(
            "/api/v1/auth/login/",
            {"email": "user-a@example.test", "password": "S3curePass!123"},
            format="json",
        )
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")

        # User A tries to modify Tenant B.
        response = api_client.patch(
            "/api/v1/tenants/me/",
            {"name": "Hacked Name"},
            format="json",
            HTTP_X_TENANT_ID=str(tenant_b.id),
        )

        assert response.status_code == 403

        # Verify Tenant B was not modified.
        tenant_b.refresh_from_db()
        assert tenant_b.name == "Globex Corp"
