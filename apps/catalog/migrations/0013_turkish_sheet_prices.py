from decimal import Decimal

from django.db import migrations

MONEY = Decimal("0.001")

PRICES = {
    "turkish-coffee-jordanian-blend": "3.750",
    "turkish-coffee-jordanian-blend-sachets": "3.750",
    "french-coffee": "3.500",
    "french-coffee-hazelnut": "3.500",
    "french-coffee-macadamia": "3.500",
    "turkish-coffee-mastic": "3.750",
    "turkish-coffee-caramel": "3.750",
    "turkish-coffee-vanilla": "3.750",
    "turkish-coffee-hazelnut-vanilla": "3.750",
    "turkish-coffee-hazelnut": "3.750",
    "turkish-coffee-macadamia": "3.750",
    "turkish-coffee-ethiopian": "3.500",
    "turkish-coffee-medium-bag": "3.500",
    "turkish-coffee-light-bag": "3.500",
    "turkish-coffee-dark-bag": "3.500",
    "turkish-coffee-colombian": "4.000",
    "turkish-coffee-no-cardamom": "3.500",
    "turkish-coffee-decaf-bag": "4.000",
    "ottoman-coffee": "4.000",
    "turkish-coffee-kenyan": "4.000",
    "turkish-coffee-chocolate": "3.750",
}


def apply_prices(apps, schema_editor):
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
        if not variant:
            continue
        variant.price = Decimal(price).quantize(MONEY)
        variant.save()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0012_sheet_prices"),
    ]

    operations = [
        migrations.RunPython(apply_prices, noop),
    ]
