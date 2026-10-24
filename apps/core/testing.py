from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import AdminRole, Permission, User
from apps.catalog.models import Category, Product, ProductVariant


def jpeg_file(name="photo.jpg", size=(8, 8), color=(40, 80, 40)) -> SimpleUploadedFile:
    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, format="JPEG", quality=85)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


def make_permission(code: str) -> Permission:
    module, _, action = code.partition(".")
    perm, _ = Permission.objects.get_or_create(
        code=code,
        defaults={"module": module or "general", "action": action or "view"},
    )
    return perm


def make_role(name: str, codes: list[str] | None = None) -> AdminRole:
    slug = name.lower().replace(" ", "-")
    role, _ = AdminRole.objects.get_or_create(name=name, defaults={"slug": slug})
    if role.slug != slug:
        role.slug = slug
        role.save(update_fields=["slug"])
    for code in codes or []:
        role.permissions.add(make_permission(code))
    return role


def make_user(
    email="customer@test.com",
    password="Customer12345!",
    *,
    staff=False,
    superuser=False,
    role=None,
    codes=None,
    **extra,
):
    defaults = {
        "first_name": extra.pop("first_name", "Test"),
        "last_name": extra.pop("last_name", "User"),
        "phone": extra.pop("phone", "0790000000"),
        "is_staff": staff or superuser,
        "is_superuser": superuser,
        "user_type": User.UserType.STAFF if staff or superuser else User.UserType.CUSTOMER,
        "role": role,
        "is_active": True,
    }
    defaults.update(extra)
    user = User.objects.create_user(email=email, password=password, **defaults)
    if codes:
        assigned = role or make_role(f"role-{email}", codes)
        user.role = assigned
        user.is_staff = True
        user.user_type = User.UserType.STAFF
        user.save(update_fields=["role", "is_staff", "user_type"])
    return user


def auth_client(user) -> APIClient:
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


def make_category(**kwargs) -> Category:
    payload = {
        "name": "Turkish Coffee",
        "slug": "turkish-coffee",
        "is_active": True,
        "show_in_nav": True,
        "display_order": 1,
    }
    payload.update(kwargs)
    obj, _ = Category.objects.get_or_create(slug=payload["slug"], defaults=payload)
    return obj


def make_product(category=None, **kwargs) -> Product:
    category = category or make_category()
    payload = {
        "category": category,
        "name": "Turkish Coffee Medium",
        "slug": "turkish-coffee-medium",
        "sku": "BCH-TR-MED-250",
        "is_active": True,
        "published_at": timezone.now(),
    }
    payload.update(kwargs)
    return Product.objects.create(**payload)


def make_variant(product=None, **kwargs) -> ProductVariant:
    product = product or make_product()
    payload = {
        "product": product,
        "name": "250g",
        "sku": f"{product.sku}-V",
        "price": Decimal("3.750"),
        "stock_quantity": 20,
        "weight_label": "250g",
        "is_active": True,
    }
    payload.update(kwargs)
    return ProductVariant.objects.create(**payload)
