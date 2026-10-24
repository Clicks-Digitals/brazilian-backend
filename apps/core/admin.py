from django.contrib import admin

from apps.core.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "entity_type", "entity_id")
    list_filter = ("action", "entity_type")
    search_fields = ("entity_id", "action", "actor__email")
    readonly_fields = (
        "actor",
        "action",
        "entity_type",
        "entity_id",
        "metadata",
        "ip_address",
        "created_at",
    )
