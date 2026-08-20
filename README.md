# Humatan CRM

A multi-tenant SaaS CRM backend, built with Django + Django REST Framework
and PostgreSQL, designed as a real-world, production-minded portfolio
project rather than a tutorial project.

**Current status: Milestone 1 — Project Foundation.** Identity and
multi-tenant infrastructure only. Customer/Lead/Deal/Activity/Task/Audit
domain models are not implemented yet — see [Roadmap](#roadmap).

## Architecture at a glance

```
Client
  |
Django / DRF
  |
Authentication (JWT)        <- Milestone 2
  |
Tenant Resolution            <- Milestone 2
  |
Authorization / RBAC         <- Milestone 6
  |
Business Logic (services/selectors)
  |
PostgreSQL
```

Full details: [`ARCHITECTURE.md`](ARCHITECTURE.md) · [`SECURITY.md`](SECURITY.md) · [`docs/decisions/`](docs/decisions/)

## Main features (Milestone 1)

- Custom, email-based `User` model
- `Tenant` model (company/organization)
- `Membership` model linking `User` <-> `Tenant` <-> `Role`, with a
  database-level uniqueness constraint (one Membership per user per
  tenant)
- A centralized tenant-isolation primitive (`TenantOwnedModel` /
  `TenantScopedQuerySet` / `tenant_context`) that every future
  tenant-owned model (Customer, Lead, Deal, ...) will build on — see
  [ADR-004](docs/decisions/ADR-004-explicit-tenant-scoping.md)
- Environment-driven settings split into `base` / `development` /
  `production`
- Normalized DRF error response format
- Dockerized local development (Django + PostgreSQL + Redis)
- CI (GitHub Actions): lint, format check, Django checks, migration-drift
  check, tests

## Technology stack

- Python 3.12, Django 5.0, Django REST Framework
- PostgreSQL 16
- `djangorestframework-simplejwt` (JWT auth — wired in Milestone 2)
- `django-environ`, `django-filter`, `drf-spectacular`
- `ruff` (lint + format), `pytest` / `pytest-django`
- Docker / Docker Compose

## Local setup

### Option A — Docker (recommended)

```bash
cp .env.example .env
# edit .env: set a real DJANGO_SECRET_KEY, and DATABASE_URL to
# postgres://humatan:humatan@db:5432/humatan_crm (matches docker-compose.yml)

docker compose up --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

The API is then available at `http://localhost:8000/`.

### Option B — Local Python + local PostgreSQL

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env
# edit .env: DATABASE_URL should point at your local PostgreSQL instance,
# e.g. postgres://postgres:postgres@localhost:5432/humatan_crm

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Environment variables

See [`.env.example`](.env.example) for the full list with placeholder
values. Key variables:

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Django's cryptographic signing key. Must be a real secret in any non-local environment. |
| `DJANGO_DEBUG` | Debug mode. Hard-disabled in `production.py` regardless of this value. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed hosts. Required (no default) in production. |
| `DATABASE_URL` | PostgreSQL connection string (`django-environ` `db()` format). |
| `REDIS_URL` | Reserved for future caching/rate-limiting — not consumed yet, see [ADR-005](docs/decisions/ADR-005-redis-provisioned-not-used.md). |
| `ACCESS_TOKEN_LIFETIME_MINUTES` / `REFRESH_TOKEN_LIFETIME_DAYS` | JWT lifetimes (Milestone 2). |
| `CORS_ALLOWED_ORIGINS` | Comma-separated origins allowed to call the API from a browser. |

## API documentation

OpenAPI schema and docs are wired via `drf-spectacular`:

- Schema: `/api/schema/`
- Swagger UI: `/api/docs/`

All routes are versioned under `/api/v1/` (see
[ADR discussion in ARCHITECTURE.md](ARCHITECTURE.md#api-surface)). No
domain endpoints exist yet — `apps/accounts/urls.py` and
`apps/tenants/urls.py` currently export empty route lists, filled in
starting Milestone 2.

## Testing

```bash
pytest                                  # run the full suite
pytest --cov=apps --cov-report=term-missing   # with coverage
ruff check .                            # lint
ruff format --check .                   # format check
python manage.py check                  # Django system checks
python manage.py makemigrations --check --dry-run   # migration drift check
```

Current coverage focuses on what exists this milestone: user
creation/uniqueness, the Membership uniqueness constraint, cross-tenant
Membership isolation, and the tenant-context/scoping mechanics
themselves. See
[`apps/core/tests/test_tenant_isolation_foundation.py`](apps/core/tests/test_tenant_isolation_foundation.py)
for the tenant-isolation tests specifically — this is the project's
highest-priority test area (spec section 62) and will keep growing
alongside every tenant-owned model added in later milestones.

## Project structure

```
humatan-crm/
├── config/
│   ├── settings/{base,development,production}.py
│   ├── urls.py, api_urls.py, asgi.py, wsgi.py
├── apps/
│   ├── core/        shared infra: base models, tenant-isolation primitives,
│   │                 exception handling
│   ├── accounts/     User, Role, Membership
│   └── tenants/      Tenant
├── tests/            (project-level test scaffolding; most tests currently
│                       live alongside each app in apps/<app>/tests/)
├── docs/
│   └── decisions/    ADR-001 .. ADR-005
├── .github/workflows/ci.yml
├── Dockerfile, docker-compose.yml
├── requirements.txt, requirements-dev.txt, pyproject.toml
├── .env.example
├── ARCHITECTURE.md, SECURITY.md
└── README.md
```

## Security model

See [`SECURITY.md`](SECURITY.md) for the full threat model and current
mitigations. Summary: tenant isolation is the top security priority in
this project (spec section 62); it's implemented via an explicit,
never-automatic scoping mechanism (`.scoped()` / `.for_tenant()`) that
raises loudly rather than failing silently when misused — see
[ADR-004](docs/decisions/ADR-004-explicit-tenant-scoping.md).

## Multi-tenancy model

Shared database, shared schema, explicit `tenant` foreign key on every
tenant-owned model (spec section 8) — not separate databases or schemas
per tenant. Full design in [`ARCHITECTURE.md`](ARCHITECTURE.md#multi-tenancy-model).

## RBAC

`User -> Membership -> Tenant -> Role`. `Role` currently ships as a fixed,
minimal lookup table (owner / sales_manager / sales_representative /
support / viewer); the full permission matrix and OWN/TEAM/TENANT data
scopes land in Milestone 6, once the domain models permissions actually
guard exist. See [ADR-003](docs/decisions/ADR-003-role-model-minimal-in-milestone-1.md).

## Roadmap

| Milestone | Scope |
|---|---|
| 1 — Project Foundation | ✅ Done — this release |
| 2 — Authentication + Tenant Access | JWT auth, `TenantResolutionMiddleware`, tenant-isolation foundation tests at the HTTP level |
| 3 — CRM Core | Customer, Contact, Lead, lead conversion |
| 4 — Sales | Pipeline, Stage, Deal |
| 5 — Activities & Tasks | Activity, customer timeline, Task |
| 6 — RBAC & Scoped Access | Permission model, OWN/TEAM/TENANT scopes |
| 7 — Dashboard / Reporting | CRM metrics and reports |
| 8 — Audit | Audit logging for business/security events |
| 9 — Production Engineering | Index/query review, caching, rate limiting |
| 10 — CI + Documentation + GitHub | Final polish for portfolio presentation |

## Architectural decisions

Each significant design decision is documented as an ADR in
[`docs/decisions/`](docs/decisions/):

- [ADR-001](docs/decisions/ADR-001-tenant-ownership-via-membership.md) — Tenant ownership derived from Membership, not a `Tenant.owner` FK
- [ADR-002](docs/decisions/ADR-002-platform-superuser-vs-tenant-rbac.md) — Platform superuser separated from Tenant RBAC
- [ADR-003](docs/decisions/ADR-003-role-model-minimal-in-milestone-1.md) — `Role` minimal for now; full RBAC in Milestone 6
- [ADR-004](docs/decisions/ADR-004-explicit-tenant-scoping.md) — Explicit (never automatic) tenant scoping
- [ADR-005](docs/decisions/ADR-005-redis-provisioned-not-used.md) — Redis provisioned, not yet consumed
