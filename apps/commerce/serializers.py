from rest_framework import serializers

from apps.commerce.models import Cart, CartItem, Discount, Order, OrderItem, OrderStatusHistory
from apps.core.utils import absolute_uri, money


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="variant.product.name", read_only=True)
    product_slug = serializers.CharField(source="variant.product.slug", read_only=True)
    variant_name = serializers.CharField(source="variant.name", read_only=True)
    sku = serializers.CharField(source="variant.sku", read_only=True)
    unit_price = serializers.SerializerMethodField()
    line_total = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    stock_quantity = serializers.IntegerField(source="variant.stock_quantity", read_only=True)

    class Meta:
        model = CartItem
        fields = (
            "id",
            "variant",
            "quantity",
            "product_name",
            "product_slug",
            "variant_name",
            "sku",
            "unit_price",
            "line_total",
            "image",
            "stock_quantity",
        )

    def get_unit_price(self, obj):
        return str(money(obj.variant.price))

    def get_line_total(self, obj):
        return str(money(obj.variant.price * obj.quantity))

    def get_image(self, obj):
        request = self.context.get("request")
        if obj.variant.image:
            return absolute_uri(request, obj.variant.image)
        image = obj.variant.product.images.order_by("-is_primary", "sort_order").first()
        return absolute_uri(request, image.image) if image else None


class CartAddSerializer(serializers.Serializer):
    variant_id = serializers.IntegerField(required=False)
    quantity = serializers.IntegerField(required=False, min_value=1, default=1)
    discount_code = serializers.CharField(required=False, allow_blank=True)


class CartItemUpdateSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=0)


class DiscountValidateSerializer(serializers.Serializer):
    code = serializers.CharField()
    cart_token = serializers.CharField(required=False, allow_blank=True)


class CheckoutCustomerSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    full_name = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)


class CheckoutAddressSerializer(serializers.Serializer):
    line1 = serializers.CharField()
    line2 = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField()
    area = serializers.CharField(required=False, allow_blank=True)
    country = serializers.CharField(required=False, allow_blank=True)
    delivery_instructions = serializers.CharField(required=False, allow_blank=True)


class CheckoutSerializer(serializers.Serializer):
    cart_token = serializers.CharField(required=False)
    customer = CheckoutCustomerSerializer()
    address = CheckoutAddressSerializer()
    payment_method = serializers.ChoiceField(choices=["cod"], default="cod")
    discount_code = serializers.CharField(required=False, allow_blank=True)
    idempotency_key = serializers.CharField(max_length=64)
    notes = serializers.CharField(required=False, allow_blank=True)


class OrderItemSerializer(serializers.ModelSerializer):
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=3, coerce_to_string=True)
    line_total = serializers.DecimalField(max_digits=12, decimal_places=3, coerce_to_string=True)

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "product_name",
            "variant_name",
            "sku",
            "quantity",
            "unit_price",
            "line_total",
        )


class OrderHistorySerializer(serializers.ModelSerializer):
    actor = serializers.CharField(source="actor.email", read_only=True)

    class Meta:
        model = OrderStatusHistory
        fields = ("id", "from_status", "to_status", "note", "actor", "created_at")


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    history = OrderHistorySerializer(many=True, read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=3, coerce_to_string=True)
    discount_amount = serializers.DecimalField(max_digits=12, decimal_places=3, coerce_to_string=True)
    delivery_fee = serializers.DecimalField(max_digits=12, decimal_places=3, coerce_to_string=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=3, coerce_to_string=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "order_number",
            "email",
            "customer_name",
            "phone",
            "shipping_line1",
            "shipping_line2",
            "shipping_city",
            "shipping_area",
            "shipping_country",
            "delivery_instructions",
            "notes",
            "internal_notes",
            "status",
            "payment_status",
            "payment_method",
            "subtotal",
            "discount_amount",
            "discount_code",
            "delivery_fee",
            "total",
            "currency",
            "placed_at",
            "updated_at",
            "items",
            "history",
        )
        read_only_fields = fields


class AdminOrderSerializer(OrderSerializer):
    class Meta(OrderSerializer.Meta):
        read_only_fields = tuple(
            f for f in OrderSerializer.Meta.fields if f not in {"internal_notes", "notes"}
        )


class DiscountSerializer(serializers.ModelSerializer):
    value = serializers.DecimalField(max_digits=10, decimal_places=3, coerce_to_string=True)
    min_order_amount = serializers.DecimalField(
        max_digits=10, decimal_places=3, coerce_to_string=True
    )
    max_discount_amount = serializers.DecimalField(
        max_digits=10, decimal_places=3, coerce_to_string=True, allow_null=True, required=False
    )

    class Meta:
        model = Discount
        fields = (
            "id",
            "code",
            "name",
            "discount_type",
            "value",
            "min_order_amount",
            "max_discount_amount",
            "usage_limit",
            "per_customer_limit",
            "starts_at",
            "ends_at",
            "is_active",
            "products",
            "categories",
            "excluded_products",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class OrderStatusSerializer(serializers.Serializer):
    status = serializers.CharField()
    note = serializers.CharField(required=False, allow_blank=True)


class PaymentStatusSerializer(serializers.Serializer):
    payment_status = serializers.CharField()


def serialize_cart(cart: Cart, request, totals: dict) -> dict:
    items = CartItemSerializer(
        cart.items.all(), many=True, context={"request": request}
    ).data
    discount = None
    if cart.discount_id:
        discount = {
            "code": cart.discount.code,
            "name": cart.discount.name,
            "discount_type": cart.discount.discount_type,
            "value": str(money(cart.discount.value)),
        }
    return {
        "token": str(cart.token),
        "items": items,
        "discount": discount,
        "subtotal": str(totals["subtotal"]),
        "discount_amount": str(totals["discount_amount"]),
        "discount_code": totals["discount_code"],
        "delivery_fee": str(totals["delivery_fee"]),
        "total": str(totals["total"]),
        "currency": totals["currency"],
    }
