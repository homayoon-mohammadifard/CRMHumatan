"""Seed the fixed set of Roles (spec section 49).

Roles are a fixed enumeration, not tenant-customizable data (see ADR-003),
so they're seeded once here via a data migration rather than created
ad-hoc (e.g. get_or_create scattered through service code), which is more
deterministic and avoids repeated existence checks / race conditions on
first use.
"""

from django.db import migrations

ROLES = [
    ("owner", "Owner", "Full control over the tenant, its settings, and all data."),
    (
        "sales_manager",
        "Sales Manager",
        "Manages a sales team; can see and manage their team's records.",
    ),
    (
        "sales_representative",
        "Sales Representative",
        "Manages their own customers, leads, and deals.",
    ),
    ("support", "Support", "Handles customer support activity."),
    ("viewer", "Viewer", "Read-only access."),
]


def seed_roles(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    for slug, name, description in ROLES:
        Role.objects.get_or_create(
            slug=slug, defaults={"name": name, "description": description}
        )


def unseed_roles(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Role.objects.filter(slug__in=[slug for slug, _, _ in ROLES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_roles, reverse_code=unseed_roles),
    ]
