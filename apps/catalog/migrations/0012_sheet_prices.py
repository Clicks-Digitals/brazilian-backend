from decimal import Decimal

from django.db import migrations

MONEY = Decimal("0.001")

PRICES = {
    # Filter
    "filter-coffee-original": ("4.000", "250g"),
    "filter-coffee-colombian": ("4.000", "250g"),
    "filter-coffee-kenyan": ("4.000", "250g"),
    "filter-coffee-ethiopian": ("4.000", "250g"),
    "filter-coffee-peru": ("4.000", "250g"),
    "filter-coffee-mastic": ("4.250", "250g"),
    "filter-coffee-vanilla": ("4.250", "250g"),
    "filter-coffee-vanilla-hazelnut": ("4.250", "250g"),
    "filter-coffee-salted-caramel": ("4.250", "250g"),
    "filter-coffee-hazelnut": ("4.250", "250g"),
    "filter-coffee-macadamia": ("4.250", "250g"),
    "filter-coffee-chocolate": ("4.250", "250g"),
    # Espresso
    "espresso-medium": ("4.000", "250g"),
    "espresso-dark": ("4.000", "250g"),
    "espresso-decaf": ("4.000", "250g"),
    # Drip
    "drip-coffee-original": ("5.000", "10 sachets"),
    "drip-coffee-decaf": ("5.000", "10 sachets"),
    "drip-coffee-hazelnut": ("5.000", "10 sachets"),
    "drip-coffee-macadamia": ("5.000", "10 sachets"),
    # Arabic / Saudi
    "arabic-coffee-10-sachets": ("10.000", "10 sachets"),
    "saudi-coffee-10-sachets": ("10.000", "10 sachets"),
    "arabic-coffee-sachet": ("1.000", "sachet"),
    "saudi-coffee-sachet": ("1.000", "sachet"),
    "arabic-coffee-bag": ("3.500", "250g"),
    "saudi-coffee-bag": ("3.500", "250g"),
    # Rio House
    "rio-house-creamer": ("3.000", "450g"),
    "rio-house-creamer-small": ("1.750", "200g"),
    "rio-house-gold": ("5.500", "200g"),
    "rio-house-black-gar": ("2.500", "200g"),
    "rio-house-3-in-1-bag": ("4.000", "30 sachets"),
    "rio-house-2-in-1-bag": ("4.000", "30 sachets"),
    "rio-house-black-500g": ("11.500", "500g"),
    "rio-house-3-in-1-1kg": ("5.500", "1kg"),
    "rio-house-hazelnut-cappuccino-1kg": ("8.000", "1kg"),
    "rio-house-caramel-cappuccino-1kg": ("8.000", "1kg"),
    "rio-house-hot-chocolate-1kg": ("8.000", "1kg"),
    "rio-house-3-in-1": ("3.500", "24 sachets"),
    "rio-house-2-in-1": ("3.500", "24 sachets"),
    "rio-house-hot-chocolate": ("2.250", "10 sachets"),
    "rio-house-hazelnut-cappuccino": ("2.250", "10 sachets"),
    "rio-house-caramel-cappuccino": ("2.250", "10 sachets"),
    "rio-house-mocha": ("2.250", "10 sachets"),
    "rio-house-black": ("2.250", "24 sachets"),
    "rio-house-lentil": ("1.500", "10 sachets"),
    "rio-house-milk-ginger": ("1.500", "10 sachets"),
    "rio-house-chai-karak": ("1.500", "box"),
    "rio-house-salep": ("1.500", "box"),
}

EXTRA_VARIANTS = [
    {
        "product": "rio-house-gold",
        "sku": "BCH-RIO-GLD-100",
        "name": "100g",
        "weight_label": "100g",
        "price": "3.500",
    },
    {
        "product": "rio-house-black-gar",
        "sku": "BCH-RIO-BLK-JAR-100",
        "name": "100g",
        "weight_label": "100g",
        "price": "4.500",
    },
    {
        "product": "rio-house-black-gar",
        "sku": "BCH-RIO-BLK-JAR-50",
        "name": "50g",
        "weight_label": "50g",
        "price": "1.500",
    },
]


def apply_prices(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    ProductVariant = apps.get_model("catalog", "ProductVariant")
    for slug, (price, weight) in PRICES.items():
        product = Product.objects.filter(slug=slug).first()
        if not product:
            continue
        variant = (
            ProductVariant.objects.filter(product=product, sku=product.sku).first()
            or ProductVariant.objects.filter(product=product).order_by("id").first()
        )
        if not variant:
            continue
        variant.price = Decimal(price).quantize(MONEY)
        variant.weight_label = weight
        variant.name = weight
        variant.save()

    for spec in EXTRA_VARIANTS:
        product = Product.objects.filter(slug=spec["product"]).first()
        if not product:
            continue
        ProductVariant.objects.update_or_create(
            sku=spec["sku"],
            defaults={
                "product_id": product.id,
                "name": spec["name"],
                "price": Decimal(spec["price"]).quantize(MONEY),
                "weight_label": spec["weight_label"],
                "stock_quantity": 20,
                "is_active": True,
            },
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0011_caffitaly_machines_order"),
    ]

    operations = [
        migrations.RunPython(apply_prices, noop),
    ]
