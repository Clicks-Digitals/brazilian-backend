from __future__ import annotations

import hashlib
from decimal import Decimal

from django.apps import apps

MONEY = Decimal("0.001")
SIZE_STEPS = (
    ("500g", Decimal("2"), "500"),
    ("1kg", Decimal("4"), "1000"),
)


def normalize_weight(value: str | None) -> str:
    return (value or "").strip().lower().replace(" ", "").replace("غ", "g")


def is_250g_variant(weight: str | None, sku: str | None, name: str | None = "") -> bool:
    for raw in (weight, name):
        if normalize_weight(raw) in {"250g", "250"}:
            return True
    return (sku or "").upper().endswith("-250")


def sized_sku(base_sku: str, suffix: str) -> str:
    sku = base_sku or ""
    if sku.upper().endswith("-250"):
        return f"{sku[:-4]}-{suffix}"
    return f"{sku}-{suffix}"


def stable_stock(sku: str) -> int:
    digest = hashlib.sha256(sku.encode("utf-8")).hexdigest()
    return 8 + (int(digest, 16) % 33)


def _money(value) -> Decimal:
    if value in (None, ""):
        return Decimal("0.000")
    return Decimal(str(value)).quantize(MONEY)


def ensure_250g_family_variants(ProductVariant=None) -> int:
    """Give every 250g variant matching 500g and 1kg options, priced from the 250g pack."""
    if ProductVariant is None:
        ProductVariant = apps.get_model("catalog", "ProductVariant")

    created_or_updated = 0
    bases = [
        variant
        for variant in ProductVariant.objects.all()
        if variant.is_active and is_250g_variant(variant.weight_label, variant.sku, variant.name)
    ]
    for variant in bases:
        for label, multiplier, suffix in SIZE_STEPS:
            sku = sized_sku(variant.sku, suffix)
            compare = None
            if getattr(variant, "compare_at_price", None):
                compare = _money(Decimal(str(variant.compare_at_price)) * multiplier)
            ProductVariant.objects.update_or_create(
                sku=sku,
                defaults={
                    "product_id": variant.product_id,
                    "name": label,
                    "price": _money(Decimal(str(variant.price)) * multiplier),
                    "compare_at_price": compare,
                    "weight_label": label,
                    "stock_quantity": stable_stock(sku),
                    "is_active": True,
                },
            )
            created_or_updated += 1
    return created_or_updated
