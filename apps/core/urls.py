from django.urls import path

from apps.core.views import AdminAuditLogView, HealthView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("admin/audit-logs/", AdminAuditLogView.as_view(), name="admin-audit-logs"),
]
