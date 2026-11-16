from django.db import migrations

BAG_PRODUCTS = (
    "turkish-coffee-medium-bag",
    "turkish-coffee-light-bag",
    "turkish-coffee-decaf-bag",
    "turkish-coffee-dark-bag",
    "filter-coffee-bag",
    "turkish-coffee-jordanian-blend-bag",
)


def restore_bags(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    ProductVariant = apps.get_model("catalog", "ProductVariant")
    for product in Product.objects.filter(slug__in=BAG_PRODUCTS):
        ProductVariant.objects.filter(product=product, sku__iendswith="-500").delete()
        ProductVariant.objects.filter(product=product, sku__iendswith="-1000").delete()
        variant = (
            ProductVariant.objects.filter(product=product, sku=product.sku).first()
            or ProductVariant.objects.filter(product=product).order_by("id").first()
        )
        if not variant:
            continue
        variant.name = "bag"
        variant.weight_label = "bag"
        variant.save()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0019_bag_size_family"),
    ]

    operations = [
        migrations.RunPython(restore_bags, noop),
    ]
