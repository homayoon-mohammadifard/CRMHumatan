"""
Tenant-facing endpoints (tenant settings, tenant management) land in a later
milestone. Empty router for now so config/api_urls.py has a stable include
target and doesn't need to change shape when those endpoints are added.
"""

app_name = "tenants"

urlpatterns = []
