
from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from apps.accounts.models import Membership, Role, User
from apps.tenants.models import Tenant
from apps.tenants.services import create_tenant


@dataclass(frozen=True)
class RegistrationResult:
    user: User
    tenant: Tenant
    membership: Membership


@transaction.atomic
def register_user_and_tenant(
    *,
    email: str,
    password: str,
    tenant_name: str,
    first_name: str = "",
    last_name: str = "",
) -> RegistrationResult:
    user = User.objects.create_user(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )
    tenant = create_tenant(tenant_name)
    owner_role = Role.objects.get(slug=Role.Slug.OWNER)
    membership = Membership.objects.create(user=user, tenant=tenant, role=owner_role)
    return RegistrationResult(user=user, tenant=tenant, membership=membership)
