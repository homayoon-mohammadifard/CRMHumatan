
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
    slug = _generate_unique_slug(name)
    return Tenant.objects.create(name=name, slug=slug)
