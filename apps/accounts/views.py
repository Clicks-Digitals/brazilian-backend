from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework import generics, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.models import AdminRole, CustomerAddress, Permission, User
from apps.accounts.serializers import (
    AddressSerializer,
    AdminCustomerSerializer,
    AdminUserSerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    PermissionSerializer,
    ProfileSerializer,
    RefreshSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    RoleSerializer,
    UserPublicSerializer,
)
from apps.accounts.services import (
    authenticate_user,
    blacklist_refresh,
    issue_tokens,
    register_user,
    reset_password,
    send_password_reset,
    set_default_address,
)
from apps.core.pagination import AdminPagination
from apps.core.permissions import HasPermissionCode, IsOwnerOrStaff, IsStaffUser
from apps.core.services import write_audit
from apps.core.throttles import AuthThrottle


def _maybe_merge_cart(request, user):
    token = request.headers.get("X-Cart-Token") or request.COOKIES.get("cart_token")
    if not token:
        return
    from apps.commerce.services import merge_guest_cart

    merge_guest_cart(user, token)


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = register_user(serializer.validated_data)
        _maybe_merge_cart(request, user)
        payload = issue_tokens(user)
        payload["user"] = UserPublicSerializer(user, context={"request": request}).data
        return Response(payload, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate_user(
            serializer.validated_data["email"], serializer.validated_data["password"]
        )
        _maybe_merge_cart(request, user)
        payload = issue_tokens(user)
        payload["user"] = UserPublicSerializer(user, context={"request": request}).data
        return Response(payload)


class AdminLoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate_user(
            serializer.validated_data["email"],
            serializer.validated_data["password"],
            staff_only=True,
        )
        payload = issue_tokens(user)
        payload["user"] = UserPublicSerializer(user, context={"request": request}).data
        return Response(payload)


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]
    serializer_class = TokenRefreshSerializer


class LogoutView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        blacklist_refresh(serializer.validated_data["refresh"])
        return Response({"detail": "Logged out."})


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        send_password_reset(serializer.validated_data["email"])
        return Response(
            {"detail": "If an account exists for this email, a reset link has been sent."}
        )


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reset_password(
            serializer.validated_data["uid"],
            serializer.validated_data["token"],
            serializer.validated_data["password"],
        )
        return Response({"detail": "Password has been reset."})


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserPublicSerializer(request.user).data)

    def patch(self, request):
        serializer = ProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserPublicSerializer(request.user).data)


class AddressListCreateView(generics.ListCreateAPIView):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return CustomerAddress.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        address = serializer.save(user=self.request.user)
        set_default_address(address)


class AddressDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrStaff]

    def get_queryset(self):
        return CustomerAddress.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        address = serializer.save()
        set_default_address(address)


class AccountOrderListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.commerce.models import Order
        from apps.commerce.serializers import OrderSerializer

        qs = (
            Order.objects.filter(Q(user=request.user) | Q(email__iexact=request.user.email))
            .prefetch_related("items")
            .order_by("-placed_at")
        )
        serializer = OrderSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)


class AccountOrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_number):
        from apps.commerce.models import Order
        from apps.commerce.serializers import OrderSerializer

        order = (
            Order.objects.filter(order_number=order_number)
            .filter(Q(user=request.user) | Q(email__iexact=request.user.email))
            .prefetch_related("items", "history", "payments")
            .first()
        )
        if not order:
            from apps.core.exceptions import APIError

            raise APIError("Order not found.", code="not_found", status=404)
        return Response(OrderSerializer(order, context={"request": request}).data)


class AdminUserViewSet(viewsets.ModelViewSet):
    serializer_class = AdminUserSerializer
    permission_classes = [IsAuthenticated, IsStaffUser, HasPermissionCode]
    pagination_class = AdminPagination
    permission_map = {
        "list": "users.view",
        "retrieve": "users.view",
        "create": "users.create",
        "update": "users.edit",
        "partial_update": "users.edit",
        "destroy": "users.delete",
    }
    search_fields = ("email", "first_name", "last_name")
    filterset_fields = ("user_type", "is_active", "is_staff")

    def get_queryset(self):
        return User.objects.select_related("role").prefetch_related("role__permissions")

    def perform_create(self, serializer):
        user = serializer.save()
        write_audit(self.request, "create", "user", user.pk, {"email": user.email})

    def perform_update(self, serializer):
        user = serializer.save()
        write_audit(self.request, "update", "user", user.pk, {"email": user.email})

    def perform_destroy(self, instance):
        write_audit(self.request, "delete", "user", instance.pk, {"email": instance.email})
        instance.delete()


class AdminRoleViewSet(viewsets.ModelViewSet):
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated, IsStaffUser, HasPermissionCode]
    pagination_class = AdminPagination
    queryset = AdminRole.objects.prefetch_related("permissions").all()
    permission_map = {
        "list": "roles.view",
        "retrieve": "roles.view",
        "create": "roles.edit",
        "update": "roles.edit",
        "partial_update": "roles.edit",
        "destroy": "roles.edit",
    }

    def perform_create(self, serializer):
        role = serializer.save()
        write_audit(self.request, "create", "role", role.pk, {"name": role.name})

    def perform_update(self, serializer):
        role = serializer.save()
        write_audit(self.request, "update", "role", role.pk, {"name": role.name})

    def perform_destroy(self, instance):
        if instance.is_system:
            from apps.core.exceptions import APIError

            raise APIError("System roles cannot be deleted.", code="conflict", status=409)
        write_audit(self.request, "delete", "role", instance.pk, {"name": instance.name})
        instance.delete()


class AdminPermissionListView(generics.ListAPIView):
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated, IsStaffUser, HasPermissionCode]
    permission_code = "roles.view"
    queryset = Permission.objects.all()
    pagination_class = None


class AdminCustomerViewSet(viewsets.ModelViewSet):
    serializer_class = AdminCustomerSerializer
    permission_classes = [IsAuthenticated, IsStaffUser, HasPermissionCode]
    pagination_class = AdminPagination
    http_method_names = ["get", "patch", "put", "head", "options"]
    permission_map = {
        "list": "customers.view",
        "retrieve": "customers.view",
        "update": "customers.edit",
        "partial_update": "customers.edit",
    }
    search_fields = ("email", "first_name", "last_name", "phone")

    def get_queryset(self):
        from apps.commerce.models import Order

        return (
            User.objects.filter(user_type=User.UserType.CUSTOMER)
            .select_related("profile")
            .annotate(
                order_count=Count("orders", distinct=True),
                total_spent=Coalesce(
                    Sum(
                        "orders__total",
                        filter=~Q(orders__status=Order.Status.CANCELLED),
                    ),
                    Value(0, output_field=DecimalField(max_digits=12, decimal_places=3)),
                ),
            )
        )
