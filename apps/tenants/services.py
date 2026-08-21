"""Service-layer operations for Tenant, per spec section 20 ("use services
for important business operations such as ... tenant creation")."""

from __future__ import annotations

from django.utils.text import slugify

from apps.tenants.models import Tenant


def _generate_unique_slug(name: str) -> str:
    base_slug = slugify(name)[:200] or "tenant"
    slug = base_slug
    suffix = 2
    while Tenant.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{suffix}"[:220]
        suffix += 1
    return slug


def create_tenant(name: str) -> Tenant:
    """Create a new Tenant with an auto-generated, unique slug.

    Slug collisions (e.g. two companies both named "Acme") are resolved by
    appending a numeric suffix rather than failing the request — the name
    field is not required to be unique, only the slug (used in URLs).
    """
    slug = _generate_unique_slug(name)
    return Tenant.objects.create(name=name, slug=slug)
