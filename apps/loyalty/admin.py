from django.contrib import admin

from apps.loyalty.models import LoyaltyAccountLink, LoyaltyTransactionReference


@admin.register(LoyaltyAccountLink)
class LoyaltyAccountLinkAdmin(admin.ModelAdmin):
    list_display = ("user", "external_member_id", "is_active", "last_synced_at")


@admin.register(LoyaltyTransactionReference)
class LoyaltyTransactionReferenceAdmin(admin.ModelAdmin):
    list_display = ("order", "status", "idempotency_key", "updated_at")
