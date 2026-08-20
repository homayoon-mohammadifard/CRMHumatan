"""
Aggregates all /api/v1/ routes.

Each app owns its own urls.py; this file only wires them together under the
versioned API prefix so a future v2 can be introduced without touching every
app's internal URL structure.
"""

from django.urls import include, path

urlpatterns = [
    path("auth/", include("apps.accounts.urls")),
    path("tenants/", include("apps.tenants.urls")),
]
