from django.db import migrations

from apps.catalog.weight_sizes import ensure_bag_kg_variants


def apply_sizes(apps, schema_editor):
    ProductVariant = apps.get_model("catalog", "ProductVariant")
    ensure_bag_kg_variants(ProductVariant)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0020_restore_bag_sizes"),
    ]

    operations = [
        migrations.RunPython(apply_sizes, noop),
    ]
