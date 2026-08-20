from __future__ import annotations

from django.db import models

from apps.core.models import TimeStampedModel


class Tenant(TimeStampedModel):
    """A company/organization using Humatan CRM.

    Design decision (ADR-001): ownership is deliberately NOT a direct FK on
    Tenant. The "owner" of a Tenant is whichever User holds an active
    Membership with Role.slug == Role.Slug.OWNER for that Tenant. Adding a
    second `owner` FK here would create two sources of truth for the same
    fact, which could silently drift out of sync (e.g. an owner Membership
    is deleted/reassigned but the `owner` FK isn't updated to match).
    """

    class Status(models.TextChoices):
        TRIALING = "trialing", "Trialing"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        CANCELLED = "cancelled", "Cancelled"

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TRIALING)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return self.name
