from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomerAddress, User
from apps.core.exceptions import APIError


def issue_tokens(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    refresh["email"] = user.email
    refresh["user_type"] = user.user_type
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


def authenticate_user(email: str, password: str, staff_only=False) -> User:
    email = User.objects.normalize_email(email).lower()
    try:
        user = User.objects.select_related("role").get(email__iexact=email)
    except User.DoesNotExist as exc:
        raise APIError("Invalid email or password.", code="invalid_credentials", status=401) from exc
    if not user.is_active or not user.check_password(password):
        raise APIError("Invalid email or password.", code="invalid_credentials", status=401)
    if staff_only and not (user.is_staff or user.user_type == User.UserType.STAFF):
        raise APIError("Staff access only.", code="permission_denied", status=403)
    return user


def register_user(data: dict) -> User:
    return User.objects.create_user(
        email=data["email"],
        password=data["password"],
        first_name=data.get("first_name", ""),
        last_name=data.get("last_name", ""),
        phone=data.get("phone", ""),
        marketing_opt_in=data.get("marketing_opt_in", False),
        user_type=User.UserType.CUSTOMER,
    )


def blacklist_refresh(token: str) -> None:
    try:
        RefreshToken(token).blacklist()
    except Exception as exc:
        raise APIError("Invalid refresh token.", code="invalid_token", status=400) from exc


def send_password_reset(email: str) -> None:
    email = User.objects.normalize_email(email).lower()
    user = User.objects.filter(email__iexact=email, is_active=True).first()
    if not user:
        return
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_url = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
    send_mail(
        subject="Reset your Brazilian Coffee House password",
        message=(
            "We received a request to reset your password.\n\n"
            f"Reset link: {reset_url}\n\n"
            "If you did not request this, you can ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )


def reset_password(uid: str, token: str, password: str) -> User:
    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError) as exc:
        raise APIError("Invalid reset token.", code="invalid_token", status=400) from exc
    if not default_token_generator.check_token(user, token):
        raise APIError("Invalid or expired reset token.", code="invalid_token", status=400)
    user.set_password(password)
    user.save(update_fields=["password"])
    return user


def set_default_address(address: CustomerAddress) -> None:
    if address.is_default:
        CustomerAddress.objects.filter(user=address.user).exclude(pk=address.pk).update(
            is_default=False
        )
