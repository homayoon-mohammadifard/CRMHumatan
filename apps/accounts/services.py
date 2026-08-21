"""Service-layer operations for accounts, per spec section 20 ("use
services for important business operations such as ... tenant creation").

Registration is a multi-step business operation (create User, create
Tenant, create an owner Membership linking them) — spec section 13 warns
against implementing this kind of operation as "a random collection of
model.save() calls inside a view," and section 23 requires a database
transaction for exactly this kind of multi-step operation.
"""

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
    """Create a new User, a new Tenant, and an owner Membership linking
    them — the signup flow for a brand-new company on Humatan CRM.

    Wrapped in a single transaction: if any step fails (e.g. a race on the
    tenant slug, though `create_tenant` already guards against that), no
    partial state (a User with no Tenant, or a Tenant with no owner) is
    left behind.
    """
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
