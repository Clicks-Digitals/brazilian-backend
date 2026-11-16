from django.db import migrations

NAMES = {
    "espresso-medium": {
        "name": "Medium Roast Espresso",
        "name_ar": "قهوة إسبريسو وسط",
    },
    "espresso-dark": {
        "name": "Dark Roast Espresso",
        "name_ar": "قهوة إسبريسو غامق",
    },
}


def apply(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    for slug, names in NAMES.items():
        Product.objects.filter(slug=slug).update(**names)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0025_remove_sachet_no_cardamom_price"),
    ]

    operations = [
        migrations.RunPython(apply, noop),
    ]
