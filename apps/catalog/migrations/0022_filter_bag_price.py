from decimal import Decimal

from django.db import migrations

MONEY = Decimal("0.001")
PRICE = Decimal("4.000")


def apply_price(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    ProductVariant = apps.get_model("catalog", "ProductVariant")
    product = Product.objects.filter(slug="filter-coffee-bag").first()
    if not product:
        return
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
        ("catalog", "0021_bag_kg_sizes"),
    ]

    operations = [
        migrations.RunPython(apply_price, noop),
    ]
