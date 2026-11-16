from decimal import Decimal

from django.db import migrations

MONEY = Decimal("0.001")
PRICE = Decimal("4.000")
SLUGS = (
    "turkish-coffee-decaf",
    "turkish-coffee-peru",
    "turkish-coffee-jordanian-blend-sachets",
)


def apply_prices(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    ProductVariant = apps.get_model("catalog", "ProductVariant")
    for product in Product.objects.filter(slug__in=SLUGS):
        variant = (
            ProductVariant.objects.filter(product=product, sku=product.sku).first()
            or ProductVariant.objects.filter(product=product).order_by("id").first()
        )
        if variant:
            variant.price = PRICE.quantize(MONEY)
            variant.save(update_fields=["price"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0017_hide_removed_turkish"),
    ]

    operations = [
        migrations.RunPython(apply_prices, noop),
    ]
