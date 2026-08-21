# Milestone 2 — Authentication + Tenant Access ✅ Complete

## What's New

### Authentication Endpoints (Fully Functional)

- **POST /api/v1/auth/register/** — Signup new company
  - Atomically creates User + Tenant + owner Membership
  - Email validation + password strength check
  - Responds with user identity + memberships

- **POST /api/v1/auth/login/** — JWT login
  - Email + password → access + refresh tokens
  - Response includes user identity + all tenant memberships
  - Client selects active tenant via X-Tenant-ID header

- **POST /api/v1/auth/logout/** — Blacklist refresh token
  - Prevents reuse of old refresh tokens
  - User remains authenticated via existing access token (until expiry)

- **POST /api/v1/auth/token/refresh/** — Get new access token
  - Refresh token → new access token
  - Standard SimpleJWT flow

- **GET /api/v1/auth/me/** — Current authenticated user
  - Returns identity + all tenant memberships
  - NOT tenant-scoped (shows all orgs user belongs to)

### Tenant Management Endpoints (Fully Functional)

- **GET /api/v1/tenants/** — List user's tenants
  - All organizations authenticated user is a member of
  - Includes role in each organization
  - Cross-tenant (not filtered to active tenant)

- **GET /api/v1/tenants/me/** — Current active tenant
  - Requires X-Tenant-ID header + valid membership
  - HasActiveTenant permission enforced
  - Read-only access

- **PATCH /api/v1/tenants/me/** — Update active tenant
  - Owner-only (IsTenantOwner permission)
  - Can update tenant name
  - Requires X-Tenant-ID header + valid membership

### Tenant Resolution Architecture

**TenantResolutionMiddleware** (`apps/accounts/middleware.py`)
- Runs on every request after authentication
- Reads `X-Tenant-ID` header (client's desired active tenant)
- **Validates** against authenticated user's real Membership rows
- Never trusts client-supplied tenant ID (spec section 8)
- Sets `request.tenant` + `request.membership` for request duration
- Binds tenant to context via `apps.core.context.tenant_context`

**Permission Classes** (`apps/tenants/permissions.py`)
- `HasActiveTenant` — requires successful tenant resolution
- `IsTenantOwner` — requires Owner role in active tenant
- Integrated with existing Django permission system

### Service Layer

**apps.accounts.services.register_user_and_tenant()**
- Multi-step signup wrapped in atomic transaction
- Prevents partial state (User without Tenant, etc.)

**apps.tenants.services.create_tenant()**
- Auto-generates unique slug from company name
- Handles collisions (Acme + Acme = acme + acme-2)

### Data Migration

**apps/accounts/migrations/0002_seed_roles.py**
- Automatically seeds the 5 fixed roles:
  - owner
  - sales_manager
  - sales_representative
  - support
  - viewer

### Testing

**60 comprehensive tests** (36 new for Milestone 2):

Test coverage includes:
- User registration (happy path + validation + duplicates)
- Login/logout/token refresh (valid + invalid credentials)
- Me endpoint (current user + memberships)
- Tenant list (user's memberships)
- Tenant detail/update (valid access + owner-only enforcement)
- Middleware tenant resolution (valid/invalid/missing headers)
- **High-priority tenant-isolation tests** (spec section 62):
  - Cross-tenant data never leaks
  - User can't access other users' tenants
  - Inactive memberships blocked
  - Non-numeric tenant IDs rejected

All tests pass against real PostgreSQL (verified).

## API Documentation

OpenAPI schema auto-generated via drf-spectacular:
- **Schema endpoint**: GET /api/docs/schema/
- **Interactive UI**: GET /api/docs/

All endpoints include authentication requirements, request/response schemas, and examples.

## Security Highlights

1. **Tenant Isolation is Mandatory**
   - X-Tenant-ID header is a hint, never trusted
   - Resolved via cross-validation against Membership rows
   - Every endpoint requires explicit permission checks

2. **JWT Best Practices**
   - Access tokens: short-lived (15 min default)
   - Refresh tokens: longer-lived (7 days default)
   - Rotation + blacklist-after-rotation enabled
   - No tenant claim in JWT (prevents stale token when switching orgs)

3. **Database-Level Constraints**
   - Unique constraint on (user, tenant) for Membership
   - Enforced by PostgreSQL, not just application code

4. **Error Responses Normalized**
   - Consistent {"detail", "code", "errors"} shape
   - No accidental information leaks from different exception types

## Next Steps (Milestone 3)

Customer, Lead, and full CRM domain models will:
- Use TenantOwnedModel (foundation from Milestone 1)
- Require X-Tenant-ID header for all scoped endpoints
- Inherit HasActiveTenant permission pattern
- All tenant-scoped operations tested per spec section 62

## Directory Layout

```
humatan-crm/
├── apps/
│   ├── accounts/
│   │   ├── middleware.py          ← TenantResolutionMiddleware
│   │   ├── services.py            ← register_user_and_tenant()
│   │   ├── serializers.py         ← Auth serializers
│   │   ├── views.py               ← Register, Login, Logout, Me
│   │   ├── migrations/0002_seed_roles.py
│   │   └── tests/test_*.py        ← Auth + middleware tests
│   ├── tenants/
│   │   ├── permissions.py         ← HasActiveTenant, IsTenantOwner
│   │   ├── serializers.py         ← Tenant serializers
│   │   ├── services.py            ← create_tenant()
│   │   ├── views.py               ← List, CurrentTenant (detail+update)
│   │   └── tests/test_tenant_views.py
│   └── core/
│       └── ... (Milestone 1 foundation)
├── config/
│   └── settings/
│       ├── base.py                ← SIMPLE_JWT config added
│       └── ...
├── README.md                       ← Updated for Milestone 2
├── ARCHITECTURE.md                 ← Updated with JWT/middleware design
├── SECURITY.md                     ← Lists auth strategy
└── git log                         ← 11 meaningful commits
```

## Testing Locally

```bash
# Install dependencies
pip install -r requirements-dev.txt

# Run migrations (includes seed_roles)
python manage.py migrate

# Run all tests
pytest -v

# Run just Milestone 2 tests
pytest apps/accounts/tests/test_auth_views.py -v
pytest apps/accounts/tests/test_middleware.py -v
pytest apps/tenants/tests/test_tenant_views.py -v

# Test via curl / Postman
POST http://localhost:8000/api/v1/auth/register/
{
  "email": "ali@acme.test",
  "password": "S3curePass!123",
  "first_name": "Ali",
  "last_name": "Ahmadi",
  "tenant_name": "Acme Company"
}

# Response (201 Created)
{
  "id": 1,
  "email": "ali@acme.test",
  "first_name": "Ali",
  "last_name": "Ahmadi",
  "memberships": [
    {
      "tenant_id": 1,
      "tenant_name": "Acme Company",
      "tenant_slug": "acme-company",
      "role": "owner",
      "role_name": "Owner",
      "is_active": true
    }
  ]
}

# Login
POST http://localhost:8000/api/v1/auth/login/
{
  "email": "ali@acme.test",
  "password": "S3curePass!123"
}

# Response (200 OK)
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": { ... }
}

# Access current tenant
GET http://localhost:8000/api/v1/tenants/me/
Headers: 
  Authorization: Bearer <access_token>
  X-Tenant-ID: 1

# Response (200 OK)
{
  "id": 1,
  "name": "Acme Company",
  "slug": "acme-company",
  "status": "trialing",
  "created_at": "2026-08-21T20:40:00Z",
  "updated_at": "2026-08-21T20:40:00Z"
}
```

## Key Design Decisions

See ARCHITECTURE.md for detailed Milestone 2 architecture review, including:
- Why X-Tenant-ID is a hint never trusted for authorization
- Why JWT carries no tenant claim
- Why middleware runs JWT decode on every request
- Performance considerations

See also `apps/accounts/middleware.py` module docstring for full tenant-resolution design.

## Statistics

- **Endpoints**: 8 fully functional (register, login, logout, refresh, me, tenant-list, tenant-detail, tenant-update)
- **Tests**: 60 (24 from Milestone 1 + 36 new), 100% passing
- **Test Coverage**: Auth flows, JWT lifecycle, tenant resolution, cross-tenant isolation, permission enforcement
- **Lines of Code**: ~2,400 (models + views + serializers + tests + middleware)
- **Git Commits**: 11 meaningful commits with Conventional Commits style
- **Documentation**: README + ARCHITECTURE.md + SECURITY.md + inline code comments

---

**Milestone 3** (CRM Core) is ready to begin. Customer, Lead, and Contact domain models will inherit the tenant-resolution foundation built here.
