from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from django.db import IntegrityError, connection, transaction
from django.db.models import Count, Prefetch, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.catalog.models import ProductVariant
from apps.cms.services import get_store_settings
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
from apps.commerce.payments import get_payment_provider
from apps.core.exceptions import APIError
from apps.core.utils import money

CART_TOKEN_HEADER = "X-Cart-Token"
CART_COOKIE = "cart_token"

STATUS_TRANSITIONS = {
    Order.Status.PENDING: {Order.Status.CONFIRMED, Order.Status.CANCELLED},
    Order.Status.CONFIRMED: {Order.Status.PROCESSING, Order.Status.CANCELLED},
    Order.Status.PROCESSING: {Order.Status.READY, Order.Status.CANCELLED},
    Order.Status.READY: {Order.Status.SHIPPED, Order.Status.CANCELLED},
    Order.Status.SHIPPED: {Order.Status.DELIVERED},
    Order.Status.DELIVERED: set(),
    Order.Status.CANCELLED: set(),
}


def parse_cart_token(raw) -> uuid.UUID | None:
    if not raw:
        return None
    try:
        return uuid.UUID(str(raw))
    except (ValueError, TypeError, AttributeError):
        return None


def cart_token_from_request(request) -> uuid.UUID | None:
    header = request.headers.get(CART_TOKEN_HEADER) or request.META.get("HTTP_X_CART_TOKEN")
    cookie = request.COOKIES.get(CART_COOKIE)
    body = None
    if hasattr(request, "data"):
        body = request.data.get("cart_token")
    return parse_cart_token(header or cookie or body)


def reload_cart(cart: Cart) -> Cart:
    return (
        Cart.objects.filter(pk=cart.pk)
        .select_related("discount")
        .prefetch_related(_item_prefetch())
        .get()
    )


def get_or_create_cart(request) -> Cart:
    user = request.user if getattr(request.user, "is_authenticated", False) else None
    token = cart_token_from_request(request)
    cart = None
    if token:
        cart = (
            Cart.objects.filter(token=token)
            .select_related("discount")
            .prefetch_related(_item_prefetch())
            .first()
        )
        if cart and user and cart.user_id is None:
            cart = merge_guest_cart(user, cart.token)
        elif cart and user and cart.user_id and cart.user_id != user.id:
            cart = None
    if user and cart is None:
        cart = (
            Cart.objects.filter(user=user)
            .select_related("discount")
            .prefetch_related(_item_prefetch())
            .order_by("-updated_at")
            .first()
        )
    if cart is None:
        cart = Cart.objects.create(user=user)
        cart = (
            Cart.objects.filter(pk=cart.pk)
            .select_related("discount")
            .prefetch_related(_item_prefetch())
            .get()
        )
    elif user and cart.user_id is None:
        cart.user = user
        cart.save(update_fields=["user", "updated_at"])
    return cart


def _item_prefetch():
    return Prefetch(
        "items",
        queryset=CartItem.objects.select_related(
            "variant", "variant__product", "variant__product__category"
        ),
    )


def merge_guest_cart(user, guest_token) -> Cart:
    token = parse_cart_token(guest_token)
    user_cart = (
        Cart.objects.filter(user=user)
        .select_related("discount")
        .prefetch_related("items__variant__product")
        .order_by("-updated_at")
        .first()
    )
    if user_cart is None:
        user_cart = Cart.objects.create(user=user)
    if not token:
        return user_cart
    guest = (
        Cart.objects.filter(token=token, user__isnull=True)
        .prefetch_related("items__variant__product")
        .first()
    )
    if not guest or guest.pk == user_cart.pk:
        return user_cart
    for item in guest.items.all():
        variant = item.variant
        cap = variant.stock_quantity
        existing = user_cart.items.filter(variant=variant).first()
        if existing:
            combined = existing.quantity + item.quantity
            if not variant.product.allow_backorder:
                combined = min(combined, cap)
            existing.quantity = max(combined, 1) if combined else existing.quantity
            if combined <= 0:
                existing.delete()
            else:
                existing.save(update_fields=["quantity", "updated_at"])
        else:
            qty = item.quantity
            if not variant.product.allow_backorder:
                qty = min(qty, cap)
            if qty > 0:
                CartItem.objects.create(cart=user_cart, variant=variant, quantity=qty)
    if guest.discount_id and not user_cart.discount_id:
        user_cart.discount = guest.discount
        user_cart.save(update_fields=["discount", "updated_at"])
    guest.delete()
    return (
        Cart.objects.filter(pk=user_cart.pk)
        .select_related("discount")
        .prefetch_related(_item_prefetch())
        .get()
    )


def add_item(cart: Cart, variant_id: int, quantity: int) -> CartItem:
    if quantity < 1:
        raise APIError("Quantity must be at least 1.", code="validation_error")
    variant = ProductVariant.objects.select_related("product").filter(pk=variant_id, is_active=True).first()
    if not variant or not variant.product.is_active:
        raise APIError("Product variant is not available.", code="not_found", status=404)
    item = cart.items.filter(variant=variant).first()
    new_qty = (item.quantity if item else 0) + quantity
    if not variant.product.allow_backorder and new_qty > variant.stock_quantity:
        raise APIError("Insufficient stock for this item.", code="out_of_stock")
    if item:
        item.quantity = new_qty
        item.save(update_fields=["quantity", "updated_at"])
        return item
    return CartItem.objects.create(cart=cart, variant=variant, quantity=quantity)


def update_item(cart: Cart, item_id: int, quantity: int) -> CartItem | None:
    item = cart.items.select_related("variant", "variant__product").filter(pk=item_id).first()
    if not item:
        raise APIError("Cart item not found.", code="not_found", status=404)
    if quantity < 1:
        item.delete()
        return None
    variant = item.variant
    if not variant.product.allow_backorder and quantity > variant.stock_quantity:
        raise APIError("Insufficient stock for this item.", code="out_of_stock")
    item.quantity = quantity
    item.save(update_fields=["quantity", "updated_at"])
    return item


def remove_item(cart: Cart, item_id: int) -> None:
    deleted, _ = cart.items.filter(pk=item_id).delete()
    if not deleted:
        raise APIError("Cart item not found.", code="not_found", status=404)


def _eligible_line_total(item: CartItem, discount: Discount) -> Decimal:
    product = item.variant.product
    if discount.excluded_products.filter(pk=product.pk).exists():
        return Decimal("0.000")
    restricted = discount.products.exists() or discount.categories.exists()
    if not restricted:
        return money(item.variant.price * item.quantity)
    if discount.products.filter(pk=product.pk).exists():
        return money(item.variant.price * item.quantity)
    if discount.categories.filter(pk=product.category_id).exists():
        return money(item.variant.price * item.quantity)
    return Decimal("0.000")


def evaluate_discount(discount: Discount, cart: Cart, email: str = "") -> Decimal:
    now = timezone.now()
    if not discount.is_active:
        raise APIError("This discount code is not active.", code="discount_invalid")
    if discount.starts_at and now < discount.starts_at:
        raise APIError("This discount code is not yet valid.", code="discount_invalid")
    if discount.ends_at and now > discount.ends_at:
        raise APIError("This discount code has expired.", code="discount_expired")
    if discount.usage_limit is not None and discount.usages.count() >= discount.usage_limit:
        raise APIError("This discount code has reached its usage limit.", code="discount_invalid")
    if discount.per_customer_limit and email:
        used = discount.usages.filter(email__iexact=email).count()
        if used >= discount.per_customer_limit:
            raise APIError("You have already used this discount code.", code="discount_invalid")
    items = list(cart.items.select_related("variant", "variant__product"))
    if not items:
        raise APIError("Cart is empty.", code="validation_error")
    subtotal = sum((money(i.variant.price * i.quantity) for i in items), Decimal("0.000"))
    if subtotal < money(discount.min_order_amount):
        raise APIError("Order does not meet the minimum amount for this discount.", code="discount_invalid")
    eligible = sum((_eligible_line_total(i, discount) for i in items), Decimal("0.000"))
    if eligible <= 0:
        raise APIError("This discount does not apply to items in the cart.", code="discount_invalid")
    if discount.discount_type == Discount.DiscountType.PERCENTAGE:
        amount = money(eligible * discount.value / Decimal("100"))
    else:
        amount = money(min(discount.value, eligible))
    if discount.max_discount_amount is not None:
        amount = min(amount, money(discount.max_discount_amount))
    return money(amount)


def apply_discount(cart: Cart, code: str, email: str = "") -> Discount:
    discount = Discount.objects.filter(code__iexact=code.strip()).first()
    if not discount:
        raise APIError("Invalid discount code.", code="discount_invalid")
    evaluate_discount(discount, cart, email=email)
    cart.discount = discount
    cart.save(update_fields=["discount", "updated_at"])
    return discount


def cart_totals(cart: Cart, email: str = "") -> dict:
    items = list(cart.items.select_related("variant", "variant__product"))
    subtotal = sum((money(i.variant.price * i.quantity) for i in items), Decimal("0.000"))
    discount_amount = Decimal("0.000")
    discount_code = ""
    if cart.discount_id:
        try:
            discount_amount = evaluate_discount(cart.discount, cart, email=email)
            discount_code = cart.discount.code
        except APIError:
            discount_amount = Decimal("0.000")
            discount_code = ""
    settings = get_store_settings()
    delivery_fee = money(settings.get("delivery_fee", "2.000"))
    free_over = money(settings.get("free_shipping_over", "25.000"))
    after_discount = max(subtotal - discount_amount, Decimal("0.000"))
    if after_discount >= free_over:
        delivery_fee = Decimal("0.000")
    total = money(after_discount + delivery_fee)
    return {
        "subtotal": money(subtotal),
        "discount_amount": money(discount_amount),
        "discount_code": discount_code,
        "delivery_fee": delivery_fee,
        "total": total,
        "currency": settings.get("currency", "JOD"),
    }


def _next_order_number() -> str:
    year = timezone.now().year
    prefix = f"BCH-{year}-"
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", [year])
    last = (
        Order.objects.filter(order_number__startswith=prefix)
        .order_by("-order_number")
        .values_list("order_number", flat=True)
        .first()
    )
    seq = 1
    if last:
        try:
            seq = int(last.rsplit("-", 1)[-1]) + 1
        except ValueError:
            seq = 1
    return f"{prefix}{seq:04d}"


@transaction.atomic
def checkout(request, payload: dict) -> Order:
    idempotency_key = (payload.get("idempotency_key") or "").strip()
    if not idempotency_key:
        raise APIError("idempotency_key is required.", code="validation_error")
    existing = Order.objects.filter(idempotency_key=idempotency_key).prefetch_related("items").first()
    if existing:
        return existing

    token = parse_cart_token(payload.get("cart_token")) or cart_token_from_request(request)
    if not token:
        raise APIError("cart_token is required.", code="validation_error")
    cart = Cart.objects.select_for_update().filter(token=token).first()
    if not cart:
        raise APIError("Cart not found.", code="not_found", status=404)
    items = list(cart.items.select_related("variant", "variant__product"))
    if not items:
        raise APIError("Cart is empty.", code="validation_error")

    payment_method = payload.get("payment_method") or Order.PaymentMethod.COD
    if payment_method != Order.PaymentMethod.COD:
        raise APIError("Only cash on delivery is available.", code="payment_not_configured")

    customer = payload.get("customer") or {}
    address = payload.get("address") or {}
    user = request.user if getattr(request.user, "is_authenticated", False) else None
    email = (customer.get("email") or (user.email if user else "")).lower()
    if not email:
        raise APIError("Customer email is required.", code="validation_error")
    name = (
        customer.get("full_name")
        or f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
        or (user.full_name if user else "")
    )
    if not name:
        raise APIError("Customer name is required.", code="validation_error")
    phone = customer.get("phone") or (user.phone if user else "")
    if not phone:
        raise APIError("Customer phone is required.", code="validation_error")
    if not address.get("line1") or not address.get("city"):
        raise APIError("Delivery address is required.", code="validation_error")

    code = (payload.get("discount_code") or "").strip()
    if code:
        apply_discount(cart, code, email=email)
        cart.refresh_from_db()

    totals = cart_totals(cart, email=email)
    if cart.discount_id:
        evaluate_discount(cart.discount, cart, email=email)

    variant_ids = [item.variant_id for item in items]
    locked = {
        v.id: v
        for v in ProductVariant.objects.select_for_update()
        .select_related("product")
        .filter(id__in=variant_ids)
    }
    for item in items:
        variant = locked.get(item.variant_id)
        if not variant or not variant.is_active or not variant.product.is_active:
            raise APIError("A product in the cart is no longer available.", code="out_of_stock")
        if not variant.product.allow_backorder and variant.stock_quantity < item.quantity:
            raise APIError(
                f"Insufficient stock for {variant.product.name}.",
                code="out_of_stock",
                details={"sku": variant.sku, "available": variant.stock_quantity},
            )

    order_number = _next_order_number()
    try:
        order = Order.objects.create(
            order_number=order_number,
            user=user,
            email=email,
            customer_name=name,
            phone=phone,
            shipping_line1=address.get("line1", ""),
            shipping_line2=address.get("line2", ""),
            shipping_city=address.get("city", ""),
            shipping_area=address.get("area", ""),
            shipping_country=address.get("country") or "Jordan",
            delivery_instructions=address.get("delivery_instructions", ""),
            notes=payload.get("notes") or "",
            status=Order.Status.PENDING,
            payment_status=Order.PaymentStatus.UNPAID,
            payment_method=Order.PaymentMethod.COD,
            subtotal=totals["subtotal"],
            discount_amount=totals["discount_amount"],
            discount_code=totals["discount_code"],
            delivery_fee=totals["delivery_fee"],
            total=totals["total"],
            currency=totals["currency"],
            idempotency_key=idempotency_key,
        )
    except IntegrityError:
        existing = Order.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return existing
        raise

    for item in items:
        variant = locked[item.variant_id]
        unit_price = money(variant.price)
        OrderItem.objects.create(
            order=order,
            product=variant.product,
            variant=variant,
            product_name=variant.product.name,
            variant_name=variant.name,
            sku=variant.sku,
            quantity=item.quantity,
            unit_price=unit_price,
            line_total=money(unit_price * item.quantity),
        )
        if variant.stock_quantity >= item.quantity:
            variant.stock_quantity -= item.quantity
        else:
            variant.stock_quantity = 0
        variant.save(update_fields=["stock_quantity", "updated_at"])

    OrderStatusHistory.objects.create(
        order=order,
        from_status="",
        to_status=Order.Status.PENDING,
        note="Order placed",
        actor=user,
    )
    get_payment_provider("cod").create_payment(order)
    if cart.discount_id:
        DiscountUsage.objects.create(
            discount=cart.discount,
            user=user,
            email=email,
            order=order,
        )
    cart.items.all().delete()
    cart.discount = None
    cart.save(update_fields=["discount", "updated_at"])
    return (
        Order.objects.filter(pk=order.pk)
        .prefetch_related("items", "history", "payments")
        .get()
    )


def transition_order_status(order: Order, new_status: str, actor=None, note="") -> Order:
    if new_status not in Order.Status.values:
        raise APIError("Invalid order status.", code="validation_error")
    if new_status == order.status:
        raise APIError("Order is already in this status.", code="validation_error")
    allowed = STATUS_TRANSITIONS.get(order.status, set())
    if new_status not in allowed:
        raise APIError(
            f"Cannot transition from {order.status} to {new_status}.",
            code="invalid_transition",
        )
    previous = order.status
    with transaction.atomic():
        locked = Order.objects.select_for_update().get(pk=order.pk)
        if new_status == Order.Status.CANCELLED and locked.status != Order.Status.CANCELLED:
            _restore_stock(locked)
        locked.status = new_status
        locked.save(update_fields=["status", "updated_at"])
        OrderStatusHistory.objects.create(
            order=locked,
            from_status=previous,
            to_status=new_status,
            note=note or "",
            actor=actor,
        )
    return locked


def _restore_stock(order: Order) -> None:
    items = order.items.select_related("variant")
    variant_ids = [i.variant_id for i in items if i.variant_id]
    locked = {
        v.id: v for v in ProductVariant.objects.select_for_update().filter(id__in=variant_ids)
    }
    for item in items:
        if not item.variant_id:
            continue
        variant = locked.get(item.variant_id)
        if not variant:
            continue
        variant.stock_quantity += item.quantity
        variant.save(update_fields=["stock_quantity", "updated_at"])


def update_payment_status(order: Order, payment_status: str) -> Order:
    if payment_status not in Order.PaymentStatus.values:
        raise APIError("Invalid payment status.", code="validation_error")
    order.payment_status = payment_status
    order.save(update_fields=["payment_status", "updated_at"])
    mapping = {
        Order.PaymentStatus.PAID: PaymentRecord.Status.COMPLETED,
        Order.PaymentStatus.FAILED: PaymentRecord.Status.FAILED,
        Order.PaymentStatus.REFUNDED: PaymentRecord.Status.REFUNDED,
        Order.PaymentStatus.PENDING: PaymentRecord.Status.PENDING,
        Order.PaymentStatus.UNPAID: PaymentRecord.Status.PENDING,
    }
    new_status = mapping.get(payment_status)
    payment = order.payments.order_by("-created_at").first()
    if payment and new_status:
        payment.status = new_status
        payment.save(update_fields=["status", "updated_at"])
    return order


def _parse_range(request):
    start = parse_date(request.query_params.get("from") or "")
    end = parse_date(request.query_params.get("to") or "")
    if start:
        start = timezone.make_aware(datetime.combine(start, datetime.min.time()))
    if end:
        end = timezone.make_aware(datetime.combine(end, datetime.max.time()))
    return start, end


def dashboard_payload(request) -> dict:
    from apps.accounts.models import User
    from apps.catalog.models import Product, ProductVariant
    from apps.cms.models import Article

    start, end = _parse_range(request)
    orders = Order.objects.all()
    if start:
        orders = orders.filter(placed_at__gte=start)
    if end:
        orders = orders.filter(placed_at__lte=end)
    active_sales = orders.exclude(status=Order.Status.CANCELLED)
    sales_total = active_sales.aggregate(s=Sum("total"))["s"] or Decimal("0.000")
    sales_paid = active_sales.filter(payment_status=Order.PaymentStatus.PAID).aggregate(s=Sum("total"))[
        "s"
    ] or Decimal("0.000")
    unpaid_cod = active_sales.filter(
        payment_method=Order.PaymentMethod.COD,
        payment_status=Order.PaymentStatus.UNPAID,
    ).aggregate(s=Sum("total"))["s"] or Decimal("0.000")
    by_status = {row["status"]: row["c"] for row in orders.values("status").annotate(c=Count("id"))}
    for value, _label in Order.Status.choices:
        by_status.setdefault(value, 0)
    sales_over_time = list(
        active_sales.annotate(day=TruncDate("placed_at"))
        .values("day")
        .annotate(total=Sum("total"), orders=Count("id"))
        .order_by("day")
    )
    best_sellers = list(
        OrderItem.objects.filter(order__in=active_sales)
        .values("product_id", "product_name", "sku")
        .annotate(quantity=Sum("quantity"), revenue=Sum("line_total"))
        .order_by("-quantity")[:10]
    )
    recent = list(
        orders.select_related("user")
        .order_by("-placed_at")[:10]
        .values(
            "id",
            "order_number",
            "customer_name",
            "email",
            "status",
            "payment_status",
            "total",
            "placed_at",
        )
    )
    low_stock_qs = ProductVariant.objects.filter(is_active=True, stock_quantity__lt=5).select_related(
        "product"
    )
    return {
        "sales": {
            "total": str(money(sales_total)),
            "paid": str(money(sales_paid)),
            "unpaid_cod": str(money(unpaid_cod)),
            "currency": "JOD",
        },
        "orders_by_status": by_status,
        "orders_count": orders.count(),
        "customers": User.objects.filter(user_type=User.UserType.CUSTOMER).count(),
        "active_products": Product.objects.filter(is_active=True).count(),
        "low_stock": {
            "count": low_stock_qs.count(),
            "items": [
                {
                    "sku": v.sku,
                    "name": v.product.name,
                    "stock_quantity": v.stock_quantity,
                }
                for v in low_stock_qs[:20]
            ],
        },
        "published_articles": Article.objects.filter(status=Article.Status.PUBLISHED).count(),
        "sales_over_time": [
            {
                "day": row["day"],
                "total": str(money(row["total"] or 0)),
                "orders": row["orders"],
            }
            for row in sales_over_time
        ],
        "best_sellers": [
            {
                "product_id": row["product_id"],
                "name": row["product_name"],
                "sku": row["sku"],
                "quantity": row["quantity"],
                "revenue": str(money(row["revenue"] or 0)),
            }
            for row in best_sellers
        ],
        "recent_orders": [
            {
                **row,
                "total": str(money(row["total"])),
            }
            for row in recent
        ],
    }
