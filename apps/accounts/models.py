from __future__ import annotations

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models

from apps.core.models import TenantOwnedModel, TimeStampedModel


class UserManager(BaseUserManager):
    """Manager for the email-based custom User model.

    Django's default UserManager assumes a `username` field; since Humatan
    CRM authenticates by email (there is no meaningful "username" concept
    for a B2B CRM identity), this manager is written from scratch rather
    than subclassing Django's default.
    """

    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """Platform-wide identity.

    A User is NOT scoped to a single Tenant. The same person may hold
    separate Memberships (with different Roles) in more than one Tenant
    (see spec section 4 / Membership below) — the backend must not assume
    a 1:1 User<->Tenant relationship even though the first UI may only
    expose a single active tenant at a time.

    `is_staff` / `is_superuser` (from PermissionsMixin) grant Django-admin
    / platform-level access — this is the "Platform Superuser" concept
    (spec section 5A) and is deliberately kept separate from Tenant RBAC
    (Membership -> Role). Business authorization must never be implemented
    as `if user.is_staff` / `if user.is_superuser` (spec section 6).
    """

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        ordering = ["email"]

    def __str__(self) -> str:
        return self.email

    def get_full_name(self) -> str:
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.email

    def get_short_name(self) -> str:
        return self.first_name or self.email


class Role(TimeStampedModel):
    """A named set of permissions a Membership can hold within a Tenant.

    Design decision (ADR-003): Milestone 1 ships Role as a minimal lookup
    table (fixed slug + display name), with NO Permission relation yet.
    The full RBAC model (a Permission model, and OWN/TEAM/TENANT data
    scopes per spec sections 6-7) is deliberately deferred to Milestone 6,
    once the domain models permissions actually guard (Customer, Lead,
    Deal, ...) exist — building the permission matrix before there's
    anything to permission-check would be speculative and likely wrong.

    The slug set below matches the roles finalized in spec section 49.
    """

    class Slug(models.TextChoices):
        OWNER = "owner", "Owner"
        SALES_MANAGER = "sales_manager", "Sales Manager"
        SALES_REPRESENTATIVE = "sales_representative", "Sales Representative"
        SUPPORT = "support", "Support"
        VIEWER = "viewer", "Viewer"

    slug = models.CharField(max_length=32, choices=Slug.choices, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Membership(TenantOwnedModel):
    """Links a User to a Tenant with a Role — the core relationship RBAC
    (spec section 6) is built on: User -> Membership -> Tenant -> Role.

    A User may hold at most one Membership per Tenant. This is enforced at
    the database level (UniqueConstraint below), not only in application
    code, per spec section 22 ("prefer database constraints where the
    database can guarantee a rule") — an application-level-only check has
    a race condition under concurrent requests that a DB constraint does
    not.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.ForeignKey(
        "accounts.Role",
        on_delete=models.PROTECT,
        related_name="memberships",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "tenant"],
                name="unique_membership_per_user_per_tenant",
            )
        ]
        indexes = [
            models.Index(fields=["tenant", "role"]),
            models.Index(fields=["tenant", "user"]),
        ]
        ordering = ["tenant_id", "user_id"]

    def __str__(self) -> str:
        return f"{self.user_id} @ {self.tenant_id} ({self.role_id})"
