from decimal import Decimal

from django.db import migrations

MONEY = Decimal("0.001")

PRICES = {
    "caffitaly-s33": "170.000",
    "caffitaly-s36": "139.000",
    "caffitaly-s18": "129.000",
    "caffitaly-s16": "139.000",
    "caffitaly-s22": "249.000",
    "caffitaly-s24": "149.000",
    "caffitaly-s27": "99.000",
    "filter-coffee-decaf": "4.000",
    "rio-house-black-gar": "4.500",
}

BLACK_JAR_VARIANTS = {
    "BCH-RIO-BLK-JAR": ("200g", "4.500"),
    "BCH-RIO-BLK-JAR-100": ("100g", "2.500"),
}


def apply(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    ProductVariant = apps.get_model("catalog", "ProductVariant")
    for slug, price in PRICES.items():
        product = Product.objects.filter(slug=slug).first()
        if not product:
            continue
        variant = (
            ProductVariant.objects.filter(product=product, sku=product.sku).first()
            or ProductVariant.objects.filter(product=product).order_by("id").first()
        )
        if variant:
            variant.price = Decimal(price).quantize(MONEY)
            variant.save(update_fields=["price"])
    for sku, (weight, price) in BLACK_JAR_VARIANTS.items():
        ProductVariant.objects.filter(sku=sku).update(
            name=weight,
            weight_label=weight,
            price=Decimal(price).quantize(MONEY),
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0022_filter_bag_price"),
    ]

    operations = [
        migrations.RunPython(apply, noop),
    ]
