from django.db import migrations

REMOVED = (
    "turkish-coffee-indian",
    "turkish-coffee-jordanian-blend-dark",
    "turkish-coffee-jordanian-blend-bag",
)


def hide_products(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    Product.objects.filter(slug__in=REMOVED).update(is_active=False)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0016_capsule_prices"),
    ]

    operations = [
        migrations.RunPython(hide_products, noop),
    ]
