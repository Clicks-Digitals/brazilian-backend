from django.db import migrations

from apps.catalog.weight_sizes import ensure_250g_family_variants


def apply_sizes(apps, schema_editor):
    ProductVariant = apps.get_model("catalog", "ProductVariant")
    ensure_250g_family_variants(ProductVariant)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0018_three_turkish_prices"),
    ]

    operations = [
        migrations.RunPython(apply_sizes, noop),
    ]
