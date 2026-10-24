from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.commerce.models import Discount, Order
from apps.commerce.serializers import (
    AdminOrderSerializer,
    CartAddSerializer,
    CartItemUpdateSerializer,
    CheckoutSerializer,
    DiscountSerializer,
    DiscountValidateSerializer,
    OrderSerializer,
    OrderStatusSerializer,
    PaymentStatusSerializer,
    serialize_cart,
)
from apps.commerce.services import (
    CART_COOKIE,
    CART_TOKEN_HEADER,
    add_item,
    apply_discount,
    cart_totals,
    checkout,
    dashboard_payload,
    evaluate_discount,
    get_or_create_cart,
    parse_cart_token,
    reload_cart,
    remove_item,
    transition_order_status,
    update_item,
    update_payment_status,
)
from apps.core.exceptions import APIError
from apps.core.pagination import AdminPagination
from apps.core.permissions import HasPermissionCode, IsStaffUser
from apps.core.services import write_audit
from apps.core.throttles import CheckoutThrottle


def _cart_response(request, cart, extra_status=None):
    email = request.user.email if getattr(request.user, "is_authenticated", False) else ""
    payload = serialize_cart(cart, request, cart_totals(cart, email=email))
    response = Response(payload, status=extra_status or status.HTTP_200_OK)
    response[CART_TOKEN_HEADER] = str(cart.token)
    response.set_cookie(
        CART_COOKIE,
        str(cart.token),
        httponly=True,
        samesite="Lax",
        max_age=60 * 60 * 24 * 30,
    )
    return response


class CartView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        cart = get_or_create_cart(request)
        return _cart_response(request, cart)

    def post(self, request):
        serializer = CartAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = get_or_create_cart(request)
        data = serializer.validated_data
        if data.get("variant_id"):
            add_item(cart, data["variant_id"], data.get("quantity") or 1)
        if data.get("discount_code"):
            email = request.user.email if request.user.is_authenticated else ""
            apply_discount(cart, data["discount_code"], email=email)
        return _cart_response(request, reload_cart(cart))


class CartItemView(APIView):
    permission_classes = [AllowAny]

    def patch(self, request, pk):
        serializer = CartItemUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = get_or_create_cart(request)
        update_item(cart, pk, serializer.validated_data["quantity"])
        return _cart_response(request, reload_cart(cart))

    def delete(self, request, pk):
        cart = get_or_create_cart(request)
        remove_item(cart, pk)
        return _cart_response(request, reload_cart(cart))


class DiscountValidateView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = DiscountValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from apps.commerce.models import Cart

        code = serializer.validated_data["code"]
        token = parse_cart_token(serializer.validated_data.get("cart_token")) or parse_cart_token(
            request.headers.get(CART_TOKEN_HEADER)
        )
        cart = None
        if token:
            cart = Cart.objects.filter(token=token).prefetch_related("items__variant__product").first()
        if cart is None:
            cart = get_or_create_cart(request)
        discount = Discount.objects.filter(code__iexact=code.strip()).first()
        if not discount:
            raise APIError("Invalid discount code.", code="discount_invalid")
        email = request.user.email if request.user.is_authenticated else ""
        amount = evaluate_discount(discount, cart, email=email)
        return Response(
            {
                "valid": True,
                "code": discount.code,
                "name": discount.name,
                "discount_amount": str(amount),
                "discount_type": discount.discount_type,
                "value": str(discount.value),
            }
        )


class CheckoutView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [CheckoutThrottle]

    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)
        existing = Order.objects.filter(idempotency_key=payload["idempotency_key"]).first()
        order = checkout(request, payload)
        status_code = status.HTTP_200_OK if existing else status.HTTP_201_CREATED
        return Response(OrderSerializer(order, context={"request": request}).data, status=status_code)


class DashboardView(APIView):
    permission_classes = [IsAuthenticated, IsStaffUser, HasPermissionCode]
    permission_code = "dashboard.view"

    def get(self, request):
        return Response(dashboard_payload(request))


class AdminOrderViewSet(viewsets.ModelViewSet):
    serializer_class = AdminOrderSerializer
    permission_classes = [IsAuthenticated, IsStaffUser, HasPermissionCode]
    pagination_class = AdminPagination
    http_method_names = ["get", "patch", "put", "head", "options"]
    search_fields = ("order_number", "email", "customer_name", "phone")
    filterset_fields = ("status", "payment_status", "payment_method")
    permission_map = {
        "list": "orders.view",
        "retrieve": "orders.view",
        "update": "orders.edit",
        "partial_update": "orders.edit",
    }

    def get_queryset(self):
        return Order.objects.prefetch_related("items", "history", "payments")


class AdminOrderStatusView(APIView):
    permission_classes = [IsAuthenticated, IsStaffUser, HasPermissionCode]
    permission_code = "orders.edit"

    def post(self, request, pk):
        serializer = OrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = Order.objects.filter(pk=pk).first()
        if not order:
            raise APIError("Order not found.", code="not_found", status=404)
        order = transition_order_status(
            order,
            serializer.validated_data["status"],
            actor=request.user,
            note=serializer.validated_data.get("note", ""),
        )
        write_audit(
            request,
            "status",
            "order",
            order.pk,
            {"order_number": order.order_number, "status": order.status},
        )
        order = Order.objects.prefetch_related("items", "history", "payments").get(pk=order.pk)
        return Response(AdminOrderSerializer(order, context={"request": request}).data)


class AdminOrderPaymentView(APIView):
    permission_classes = [IsAuthenticated, IsStaffUser, HasPermissionCode]
    permission_code = "orders.edit"

    def post(self, request, pk):
        serializer = PaymentStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = Order.objects.filter(pk=pk).first()
        if not order:
            raise APIError("Order not found.", code="not_found", status=404)
        order = update_payment_status(order, serializer.validated_data["payment_status"])
        write_audit(
            request,
            "payment",
            "order",
            order.pk,
            {"order_number": order.order_number, "payment_status": order.payment_status},
        )
        order = Order.objects.prefetch_related("items", "history", "payments").get(pk=order.pk)
        return Response(AdminOrderSerializer(order, context={"request": request}).data)


class AdminDiscountViewSet(viewsets.ModelViewSet):
    serializer_class = DiscountSerializer
    permission_classes = [IsAuthenticated, IsStaffUser, HasPermissionCode]
    pagination_class = AdminPagination
    queryset = Discount.objects.prefetch_related("products", "categories", "excluded_products")
    search_fields = ("code", "name")
    permission_map = {
        "list": "discounts.view",
        "retrieve": "discounts.view",
        "create": "discounts.create",
        "update": "discounts.edit",
        "partial_update": "discounts.edit",
        "destroy": "discounts.delete",
    }

    def perform_create(self, serializer):
        obj = serializer.save()
        write_audit(self.request, "create", "discount", obj.pk, {"code": obj.code})

    def perform_update(self, serializer):
        obj = serializer.save()
        write_audit(self.request, "update", "discount", obj.pk, {"code": obj.code})

    def perform_destroy(self, instance):
        write_audit(self.request, "delete", "discount", instance.pk, {"code": instance.code})
        instance.delete()
