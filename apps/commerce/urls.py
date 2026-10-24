from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.commerce.views import (
    AdminDiscountViewSet,
    AdminOrderPaymentView,
    AdminOrderStatusView,
    AdminOrderViewSet,
    CartItemView,
    CartView,
    CheckoutView,
    DashboardView,
    DiscountValidateView,
)

router = DefaultRouter()
router.register("admin/orders", AdminOrderViewSet, basename="admin-orders")
router.register("admin/discounts", AdminDiscountViewSet, basename="admin-discounts")

urlpatterns = [
    path("cart/", CartView.as_view(), name="cart"),
    path("cart/items/<int:pk>/", CartItemView.as_view(), name="cart-item"),
    path("discounts/validate/", DiscountValidateView.as_view(), name="discount-validate"),
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("admin/dashboard/", DashboardView.as_view(), name="admin-dashboard"),
    path("admin/orders/<int:pk>/status/", AdminOrderStatusView.as_view(), name="admin-order-status"),
    path("admin/orders/<int:pk>/payment/", AdminOrderPaymentView.as_view(), name="admin-order-payment"),
    path("", include(router.urls)),
]
