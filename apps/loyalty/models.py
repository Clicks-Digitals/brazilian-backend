from django.conf import settings
from django.db import models


class LoyaltyAccountLink(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="loyalty_link"
    )
    external_member_id = models.CharField(max_length=120, blank=True)
    wallet_pass_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=False)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.user.email} loyalty link"


class LoyaltyTransactionReference(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUBMITTED = "submitted", "Submitted"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    order = models.ForeignKey(
        "commerce.Order", on_delete=models.CASCADE, related_name="loyalty_transactions"
    )
    idempotency_key = models.CharField(max_length=80, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    external_reference = models.CharField(max_length=120, blank=True)
    error_message = models.CharField(max_length=255, blank=True)
    payload_snapshot = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.order.order_number} {self.status}"
