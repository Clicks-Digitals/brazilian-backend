from django.contrib import admin

from apps.commerce.models import (
    Cart,
    CartItem,
    Discount,
    DiscountUsage,
    Order,
    OrderItem,
    OrderStatusHistory,
    PaymentRecord,
)


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("token", "user", "discount", "updated_at")
    inlines = [CartItemInline]


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_type", "value", "is_active", "min_order_amount")
    search_fields = ("code", "name")
    filter_horizontal = ("products", "categories", "excluded_products")


@admin.register(DiscountUsage)
class DiscountUsageAdmin(admin.ModelAdmin):
    list_display = ("discount", "email", "used_at")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "variant_name", "sku", "quantity", "unit_price", "line_total")


class HistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ("from_status", "to_status", "note", "actor", "created_at")


class PaymentInline(admin.TabularInline):
    model = PaymentRecord
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "customer_name",
        "status",
        "payment_status",
        "total",
        "placed_at",
    )
    list_filter = ("status", "payment_status", "payment_method")
    search_fields = ("order_number", "email", "customer_name")
    inlines = [OrderItemInline, HistoryInline, PaymentInline]


@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = ("order", "provider", "status", "amount", "created_at")
