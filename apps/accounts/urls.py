from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import (
    AccountOrderDetailView,
    AccountOrderListView,
    AddressDetailView,
    AddressListCreateView,
    AdminCustomerViewSet,
    AdminLoginView,
    AdminPermissionListView,
    AdminRoleViewSet,
    AdminUserViewSet,
    ForgotPasswordView,
    LoginView,
    LogoutView,
    ProfileView,
    RefreshView,
    RegisterView,
    ResetPasswordView,
)

router = DefaultRouter()
router.register("admin/users", AdminUserViewSet, basename="admin-users")
router.register("admin/roles", AdminRoleViewSet, basename="admin-roles")
router.register("admin/customers", AdminCustomerViewSet, basename="admin-customers")

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/forgot-password/", ForgotPasswordView.as_view(), name="auth-forgot-password"),
    path("auth/reset-password/", ResetPasswordView.as_view(), name="auth-reset-password"),
    path("admin/auth/login/", AdminLoginView.as_view(), name="admin-auth-login"),
    path("account/", ProfileView.as_view(), name="account-profile"),
    path("account/addresses/", AddressListCreateView.as_view(), name="account-addresses"),
    path("account/addresses/<int:pk>/", AddressDetailView.as_view(), name="account-address-detail"),
    path("account/orders/", AccountOrderListView.as_view(), name="account-orders"),
    path(
        "account/orders/<str:order_number>/",
        AccountOrderDetailView.as_view(),
        name="account-order-detail",
    ),
    path("admin/permissions/", AdminPermissionListView.as_view(), name="admin-permissions"),
    path("", include(router.urls)),
]
