from decimal import Decimal

from django.db import migrations

MONEY = Decimal("0.001")

GOLD = {
    "BCH-RIO-GLD": ("200g", "5.500"),
    "BCH-RIO-GLD-100": ("100g", "3.500"),
}

FRENCH = {
    "french-coffee": {
        "name": "French Original",
        "name_ar": "فرنسية أورجينال",
        "price": "3.500",
    },
    "french-coffee-hazelnut": {
        "name": "French Hazelnut",
        "name_ar": "فرنسية بالبندق",
        "price": "3.500",
    },
    "french-coffee-macadamia": {
        "name": "French Macadamia",
        "name_ar": "فرنسية بالمكاديميا",
        "price": "3.500",
    },
}


def apply(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    ProductVariant = apps.get_model("catalog", "ProductVariant")
    for sku, (weight, price) in GOLD.items():
        ProductVariant.objects.filter(sku=sku).update(
            name=weight,
            weight_label=weight,
            price=Decimal(price).quantize(MONEY),
        )
    for slug, names in FRENCH.items():
        product = Product.objects.filter(slug=slug).first()
        if not product:
            continue
        product.name = names["name"]
        product.name_ar = names["name_ar"]
        product.save(update_fields=["name", "name_ar"])
        variant = (
            ProductVariant.objects.filter(product=product, sku=product.sku).first()
            or ProductVariant.objects.filter(product=product).order_by("id").first()
        )
        if variant:
            variant.price = Decimal(names["price"]).quantize(MONEY)
            variant.save(update_fields=["price"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0026_espresso_roast_names"),
    ]

    operations = [
        migrations.RunPython(apply, noop),
    ]
