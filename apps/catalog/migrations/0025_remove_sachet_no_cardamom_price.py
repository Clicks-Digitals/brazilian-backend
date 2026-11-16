from decimal import Decimal

from django.db import migrations

MONEY = Decimal("0.001")


def apply(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    ProductVariant = apps.get_model("catalog", "ProductVariant")
    Product.objects.filter(slug="turkish-coffee-sachet").update(is_active=False)
    product = Product.objects.filter(slug="turkish-coffee-no-cardamom").first()
    if not product:
        return
    variant = (
        ProductVariant.objects.filter(product=product, sku=product.sku).first()
        or ProductVariant.objects.filter(product=product).order_by("id").first()
    )
    if variant:
        variant.price = Decimal("3.750").quantize(MONEY)
        variant.save(update_fields=["price"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0024_pack_sort_prices"),
    ]

    operations = [
        migrations.RunPython(apply, noop),
    ]
