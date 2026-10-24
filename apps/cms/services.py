from datetime import datetime

import bleach
from django.db.models import Prefetch, Q
from django.utils import timezone

from apps.catalog.models import Category, Product, ProductImage, ProductVariant
from apps.catalog.services import public_category_queryset, public_product_queryset
from apps.cms.models import Announcement, Article, Banner, LegalPage, StoreSetting
from apps.core.utils import absolute_uri

ALLOWED_TAGS = [
    "p",
    "br",
    "strong",
    "b",
    "em",
    "i",
    "u",
    "h2",
    "h3",
    "h4",
    "ul",
    "ol",
    "li",
    "a",
    "blockquote",
    "img",
    "figure",
    "figcaption",
    "span",
    "hr",
]
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "rel", "target"],
    "img": ["src", "alt", "title"],
    "span": ["class"],
    "p": ["class"],
}


def sanitize_html(value: str) -> str:
    if not value:
        return ""
    return bleach.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,
    )


def get_store_settings() -> dict:
    row = StoreSetting.objects.filter(key="store").first()
    return dict(row.value) if row else {}


def update_store_settings(payload: dict) -> dict:
    current = get_store_settings()
    current.update(payload)
    StoreSetting.objects.update_or_create(key="store", defaults={"value": current})
    return current


def active_window(qs, now=None):
    now = now or timezone.now()
    return qs.filter(is_active=True).filter(
        Q(starts_at__isnull=True) | Q(starts_at__lte=now),
        Q(ends_at__isnull=True) | Q(ends_at__gte=now),
    )


def article_related_products(article, limit=3):
    assigned = [product for product in article.related_products.all() if getattr(product, "is_active", True)]
    picked = assigned[:limit]
    if len(picked) >= limit:
        return picked
    seen = {product.id for product in picked}
    extras = public_product_queryset().exclude(id__in=seen).order_by("-is_featured", "name")[: limit - len(picked)]
    return picked + list(extras)


def published_articles():
    now = timezone.now()
    return (
        Article.objects.filter(status=Article.Status.PUBLISHED)
        .filter(Q(published_at__isnull=True) | Q(published_at__lte=now))
        .select_related("category", "author")
        .prefetch_related(
            Prefetch("related_products", queryset=public_product_queryset()),
        )
    )


def public_banners(placement=None):
    qs = active_window(Banner.objects.all())
    if placement:
        qs = qs.filter(placement=placement)
    return qs


def public_announcements():
    return active_window(Announcement.objects.all())


def storefront_payload(request) -> dict:
    from apps.catalog.serializers import CategorySerializer, ProductListSerializer
    from apps.cms.serializers import (
        AnnouncementSerializer,
        ArticleListSerializer,
        BannerSerializer,
        settings_payload,
    )

    categories = public_category_queryset().filter(show_in_nav=True)[:12]
    featured = public_product_queryset().filter(is_featured=True).order_by("-created_at")[:8]
    newest = public_product_queryset().filter(is_new=True).order_by("-created_at")[:8]
    if not newest:
        newest = public_product_queryset().order_by("-created_at")[:8]
    articles = published_articles()[:3]
    return {
        "announcements": AnnouncementSerializer(
            public_announcements(), many=True, context={"request": request}
        ).data,
        "hero_banners": BannerSerializer(
            public_banners(Banner.Placement.HERO), many=True, context={"request": request}
        ).data,
        "promo_banners": BannerSerializer(
            public_banners(Banner.Placement.PROMO), many=True, context={"request": request}
        ).data,
        "categories": CategorySerializer(categories, many=True, context={"request": request}).data,
        "featured_products": ProductListSerializer(
            featured, many=True, context={"request": request}
        ).data,
        "new_products": ProductListSerializer(newest, many=True, context={"request": request}).data,
        "articles": ArticleListSerializer(articles, many=True, context={"request": request}).data,
        "settings": settings_payload(request),
    }


def settings_payload(request) -> dict:
    data = get_store_settings()
    logo = data.get("logo")
    if logo:
        data = {**data, "logo": absolute_uri(request, logo)}
    return data
