from django.db import migrations

NAMES = {
    "caffitaly-vigoroso": {
        "name": "Caffitaly Vigoroso",
        "name_ar": "Caffitaly Vigoroso",
    },
    "compatible-soave": {
        "name": "Compatible Nespresso Soave",
        "name_ar": "Compatible Nespresso Soave",
    },
    "compatible-ethiopia": {
        "name": "Compatible Nespresso Ethiopia",
        "name_ar": "Compatible Nespresso Ethiopia",
    },
    "compatible-vivace": {
        "name": "Compatible Nespresso Vivace",
        "name_ar": "Compatible Nespresso Vivace",
    },
    "compatible-deca": {
        "name": "Compatible Nespresso Deca",
        "name_ar": "Compatible Nespresso Deca",
    },
    "compatible-deciso": {
        "name": "Compatible Nespresso Deciso Capsules",
    },
}


def apply_names(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    for slug, fields in NAMES.items():
        Product.objects.filter(slug=slug).update(**fields)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0014_250g_family_sizes"),
    ]

    operations = [
        migrations.RunPython(apply_names, noop),
    ]
