from django.db.models import Case, Count, IntegerField, Min, OuterRef, Prefetch, Q, Subquery, Sum, Value, When
from django.db.models.functions import Coalesce

from apps.catalog.models import Category, Product, ProductImage, ProductVariant


def variant_queryset(active_only=True):
    qs = ProductVariant.objects.all()
    if active_only:
        qs = qs.filter(is_active=True)
    return qs.annotate(
        size_rank=Case(
            When(weight_label__iexact="250g", then=Value(1)),
            When(weight_label__iexact="500g", then=Value(2)),
            When(weight_label__iexact="1kg", then=Value(3)),
            When(weight_label__iexact="1000g", then=Value(3)),
            default=Value(50),
            output_field=IntegerField(),
        )
    ).order_by("size_rank", "id")


def public_product_queryset():
    from apps.commerce.models import Order, OrderItem

    qty_sub = (
        OrderItem.objects.filter(product_id=OuterRef("pk"))
        .exclude(order__status=Order.Status.CANCELLED)
        .values("product")
        .annotate(qty=Sum("quantity"))
        .values("qty")[:1]
    )
    return (
        Product.objects.filter(is_active=True)
        .select_related("category")
        .prefetch_related(
            Prefetch("images", queryset=ProductImage.objects.order_by("sort_order", "id")),
            Prefetch("variants", queryset=variant_queryset()),
        )
        .annotate(
            min_price=Min("variants__price", filter=Q(variants__is_active=True)),
            units_sold=Coalesce(Subquery(qty_sub, output_field=IntegerField()), 0),
        )
    )


def admin_product_queryset():
    return Product.objects.select_related("category").prefetch_related("images", "variants").all()


def public_category_queryset():
    return Category.objects.filter(is_active=True).annotate(
        product_count=Count("products", filter=Q(products__is_active=True))
    )


def apply_product_ordering(qs, ordering: str | None):
    mapping = {
        "-created_at": ("-created_at",),
        "created_at": ("created_at",),
        "price": ("min_price", "name"),
        "-price": ("-min_price", "name"),
        "name": ("name",),
        "-name": ("-name",),
        "best_selling": ("-units_sold", "name"),
    }
    if ordering in mapping:
        return qs.order_by(*mapping[ordering])
    return qs.annotate(
        shelf_order=Case(
            When(display_order=0, then=Value(9999)),
            default="display_order",
            output_field=IntegerField(),
        )
    ).order_by("shelf_order", "name")


def related_products_for(product: Product, limit: int = 4):
    qs = public_product_queryset().exclude(pk=product.pk)
    same = list(qs.filter(category_id=product.category_id).order_by("display_order", "name")[:limit])
    if len(same) >= limit:
        return same
    seen = {item.id for item in same} | {product.id}
    extras = list(
        qs.exclude(id__in=seen).order_by("-is_featured", "-is_new", "name")[: limit - len(same)]
    )
    return same + extras


def set_primary_image(image: ProductImage):
    if image.is_primary:
        ProductImage.objects.filter(product=image.product).exclude(pk=image.pk).update(
            is_primary=False
        )
