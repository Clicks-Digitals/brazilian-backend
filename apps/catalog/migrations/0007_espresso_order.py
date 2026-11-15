from django.db import migrations


ESPRESSO_ORDER = {
    "espresso-medium": 1,
    "espresso-dark": 2,
    "espresso-decaf": 3,
}

NAME_UPDATES = {
    "espresso-medium": {
        "name": "Original Espresso",
        "name_ar": "قهوة إسبريسو الأصلية",
    },
    "espresso-dark": {
        "name": "Dark Espresso",
        "name_ar": "قهوة إسبريسو غامق",
    },
}


def apply_order(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    for slug, order in ESPRESSO_ORDER.items():
        Product.objects.filter(slug=slug).update(display_order=order)
    for slug, names in NAME_UPDATES.items():
        Product.objects.filter(slug=slug).update(**names)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0006_drip_coffee_order"),
    ]

    operations = [
        migrations.RunPython(apply_order, noop),
    ]
