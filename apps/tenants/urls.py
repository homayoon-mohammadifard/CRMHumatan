
from django.urls import path

from apps.tenants.views import CurrentTenantView, TenantListView

app_name = "tenants"

urlpatterns = [
    path("", TenantListView.as_view(), name="list"),
    path("me/", CurrentTenantView.as_view(), name="current"),
]
