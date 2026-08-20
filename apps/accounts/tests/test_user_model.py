import pytest
from django.db import IntegrityError

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


class TestUserManager:
    def test_create_user_normalizes_email_and_hashes_password(self):
        user = User.objects.create_user(email="Rep@Example.com", password="s3cure-pass")

        assert user.email == "Rep@example.com"  # domain part lowercased by normalize_email
        assert user.check_password("s3cure-pass") is True
        assert user.password != "s3cure-pass"
        assert user.is_staff is False
        assert user.is_superuser is False
        assert user.is_active is True

    def test_create_user_requires_email(self):
        with pytest.raises(ValueError):
            User.objects.create_user(email="", password="whatever")

    def test_create_superuser_sets_staff_and_superuser_flags(self):
        admin = User.objects.create_superuser(email="admin@humatan.dev", password="s3cure-pass")

        assert admin.is_staff is True
        assert admin.is_superuser is True

    def test_create_superuser_rejects_is_staff_false(self):
        with pytest.raises(ValueError):
            User.objects.create_superuser(email="admin@humatan.dev", password="x", is_staff=False)

    def test_email_uniqueness_enforced_at_db_level(self):
        User.objects.create_user(email="dup@example.com", password="s3cure-pass")
        with pytest.raises(IntegrityError):
            User.objects.create_user(email="dup@example.com", password="other-pass")


class TestUserModel:
    def test_get_full_name_falls_back_to_email(self):
        user = User.objects.create_user(email="noname@example.com", password="x")
        assert user.get_full_name() == "noname@example.com"

    def test_get_full_name_combines_first_and_last(self):
        user = User.objects.create_user(
            email="ali@example.com", password="x", first_name="Ali", last_name="Ahmadi"
        )
        assert user.get_full_name() == "Ali Ahmadi"

    def test_str_returns_email(self):
        user = User.objects.create_user(email="str@example.com", password="x")
        assert str(user) == "str@example.com"
