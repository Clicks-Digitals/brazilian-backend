import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Cart(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="carts",
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    discount = models.ForeignKey(
        "Discount", null=True, blank=True, on_delete=models.SET_NULL, related_name="carts"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return str(self.token)


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey("catalog.ProductVariant", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("cart", "variant")

    def __str__(self) -> str:
        return f"{self.variant.sku} x{self.quantity}"


class Discount(models.Model):
    class DiscountType(models.TextChoices):
        PERCENTAGE = "percentage", "Percentage"
        FIXED = "fixed", "Fixed amount"

    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=120)
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices)
    value = models.DecimalField(max_digits=10, decimal_places=3)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    per_customer_limit = models.PositiveIntegerField(null=True, blank=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    products = models.ManyToManyField("catalog.Product", blank=True, related_name="discounts")
    categories = models.ManyToManyField("catalog.Category", blank=True, related_name="discounts")
    excluded_products = models.ManyToManyField(
        "catalog.Product", blank=True, related_name="excluded_from_discounts"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.code


class DiscountUsage(models.Model):
    discount = models.ForeignKey(Discount, on_delete=models.CASCADE, related_name="usages")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    email = models.EmailField(blank=True)
    order = models.ForeignKey("Order", null=True, blank=True, on_delete=models.SET_NULL)
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["discount", "email"])]


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending confirmation"
        CONFIRMED = "confirmed", "Confirmed"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready for dispatch"
        SHIPPED = "shipped", "Out for delivery"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        REFUNDED = "refunded", "Refunded"
        FAILED = "failed", "Failed"

    class PaymentMethod(models.TextChoices):
        COD = "cod", "Cash on Delivery"

    order_number = models.CharField(max_length=24, unique=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orders",
    )
    email = models.EmailField()
    customer_name = models.CharField(max_length=180)
    phone = models.CharField(max_length=32)
    shipping_line1 = models.CharField(max_length=255)
    shipping_line2 = models.CharField(max_length=255, blank=True)
    shipping_city = models.CharField(max_length=120)
    shipping_area = models.CharField(max_length=120, blank=True)
    shipping_country = models.CharField(max_length=80, default="Jordan")
    delivery_instructions = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    payment_status = models.CharField(
        max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID
    )
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.COD
    )
    subtotal = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    discount_code = models.CharField(max_length=40, blank=True)
    delivery_fee = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    currency = models.CharField(max_length=8, default="JOD")
    idempotency_key = models.CharField(max_length=64, unique=True, null=True, blank=True)
    placed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-placed_at"]
        indexes = [
            models.Index(fields=["status", "placed_at"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self) -> str:
        return self.order_number


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", null=True, on_delete=models.SET_NULL)
    variant = models.ForeignKey("catalog.ProductVariant", null=True, on_delete=models.SET_NULL)
    product_name = models.CharField(max_length=200)
    variant_name = models.CharField(max_length=120, blank=True)
    sku = models.CharField(max_length=64)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=3)
    line_total = models.DecimalField(max_digits=12, decimal_places=3)

    def __str__(self) -> str:
        return f"{self.sku} x{self.quantity}"


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="history")
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    note = models.CharField(max_length=255, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class PaymentRecord(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments")
    provider = models.CharField(max_length=40, default="cod")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    amount = models.DecimalField(max_digits=12, decimal_places=3)
    currency = models.CharField(max_length=8, default="JOD")
    transaction_reference = models.CharField(max_length=120, blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.order.order_number} {self.provider} {self.status}"
