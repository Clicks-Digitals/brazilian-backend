from decimal import Decimal

from django.db import migrations

MONEY = Decimal("0.001")

PRICES = {
    "turkish-coffee-ethiopian": "4.000",
    "turkish-coffee-jordanian-blend-light": "3.750",
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


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0023_machines_nicaragua_rio"),
    ]

    operations = [
        migrations.RunPython(apply, noop),
    ]
