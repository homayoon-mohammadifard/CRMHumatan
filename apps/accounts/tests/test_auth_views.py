import pytest

pytestmark = pytest.mark.django_db


class TestLoginView:
    def test_login_with_valid_credentials_returns_tokens_and_user(
        self, api_client, make_user, tenant_a, owner_role, make_membership
    ):
        user = make_user(email="owner@acme.test")
        make_membership(user=user, tenant=tenant_a, role=owner_role)

        response = api_client.post(
            "/api/v1/auth/login/",
            {"email": "owner@acme.test", "password": "S3curePass!123"},
            format="json",
        )

        assert response.status_code == 200, response.data
        assert "access" in response.data
        assert "refresh" in response.data
        assert response.data["user"]["email"] == "owner@acme.test"
        assert response.data["user"]["memberships"][0]["tenant_name"] == "Acme Company"

    def test_login_with_wrong_password_is_rejected(self, api_client, make_user):
        make_user(email="user@example.test")

        response = api_client.post(
            "/api/v1/auth/login/",
            {"email": "user@example.test", "password": "wrong-password"},
            format="json",
        )

        assert response.status_code == 401

    def test_login_with_unknown_email_is_rejected(self, api_client):
        response = api_client.post(
            "/api/v1/auth/login/",
            {"email": "nobody@example.test", "password": "whatever123"},
            format="json",
        )

        assert response.status_code == 401


class TestTokenRefreshView:
    def test_refresh_returns_new_access_token(self, api_client, make_user):
        make_user(email="user@example.test")
        login = api_client.post(
            "/api/v1/auth/login/",
            {"email": "user@example.test", "password": "S3curePass!123"},
            format="json",
        )

        response = api_client.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": login.data["refresh"]},
            format="json",
        )

        assert response.status_code == 200
        assert "access" in response.data
        assert response.data["access"] != login.data["access"]

    def test_refresh_with_invalid_token_is_rejected(self, api_client):
        response = api_client.post(
            "/api/v1/auth/token/refresh/", {"refresh": "not-a-real-token"}, format="json"
        )

        assert response.status_code == 401


class TestLogoutView:
    def test_logout_blacklists_refresh_token(self, api_client, make_user):
        make_user(email="user@example.test")
        login = api_client.post(
            "/api/v1/auth/login/",
            {"email": "user@example.test", "password": "S3curePass!123"},
            format="json",
        )
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

        logout_response = api_client.post(
            "/api/v1/auth/logout/", {"refresh": login.data["refresh"]}, format="json"
        )
        assert logout_response.status_code == 204

        # The blacklisted refresh token can no longer be used.
        api_client.credentials()
        reuse_response = api_client.post(
            "/api/v1/auth/token/refresh/",
            {"refresh": login.data["refresh"]},
            format="json",
        )
        assert reuse_response.status_code == 401

    def test_logout_requires_authentication(self, api_client, make_user):
        make_user(email="user@example.test")
        login = api_client.post(
            "/api/v1/auth/login/",
            {"email": "user@example.test", "password": "S3curePass!123"},
            format="json",
        )

        response = api_client.post(
            "/api/v1/auth/logout/", {"refresh": login.data["refresh"]}, format="json"
        )

        assert response.status_code == 401

    def test_logout_without_refresh_field_is_rejected(self, authed_client):
        client, _user = authed_client

        response = client.post("/api/v1/auth/logout/", {}, format="json")

        assert response.status_code == 400
        assert "refresh" in response.data["errors"]


class TestMeView:
    def test_me_requires_authentication(self, api_client):
        response = api_client.get("/api/v1/auth/me/")
        assert response.status_code == 401

    def test_me_returns_current_user_and_memberships(
        self, authed_client, tenant_a, owner_role, make_membership
    ):
        client, user = authed_client
        make_membership(user=user, tenant=tenant_a, role=owner_role)

        response = client.get("/api/v1/auth/me/")

        assert response.status_code == 200
        assert response.data["email"] == user.email
        assert len(response.data["memberships"]) == 1
        assert response.data["memberships"][0]["tenant_name"] == "Acme Company"
        assert response.data["memberships"][0]["role"] == "owner"

    def test_me_lists_memberships_across_multiple_tenants(
        self,
        authed_client,
        tenant_a,
        tenant_b,
        owner_role,
        sales_rep_role,
        make_membership,
    ):
        client, user = authed_client
        make_membership(user=user, tenant=tenant_a, role=owner_role)
        make_membership(user=user, tenant=tenant_b, role=sales_rep_role)

        response = client.get("/api/v1/auth/me/")

        assert response.status_code == 200
        assert len(response.data["memberships"]) == 2
