from decimal import Decimal

from django.db import migrations

MONEY = Decimal("0.001")
PRICE = Decimal("4.000")


def apply_prices(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Product = apps.get_model("catalog", "Product")
    ProductVariant = apps.get_model("catalog", "ProductVariant")
    category = Category.objects.filter(slug="caffitaly-capsules").first()
    if not category:
        return
    for product in Product.objects.filter(category=category):
        ProductVariant.objects.filter(product=product).update(price=PRICE.quantize(MONEY))


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0015_capsule_display_names"),
    ]

    operations = [
        migrations.RunPython(apply_prices, noop),
    ]
