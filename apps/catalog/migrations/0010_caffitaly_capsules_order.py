from django.db import migrations


CAFFITALY_ORDER = {
    "compatible-soave": 1,
    "compatible-ethiopia": 2,
    "caffitaly-corposo": 3,
    "caffitaly-vigoroso": 4,
    "caffitaly-decaffeinato": 5,
    "caffitaly-cremoso": 6,
    "compatible-deca": 7,
    "caffitaly-intenso": 8,
    "compatible-vivace": 9,
    "compatible-deciso": 10,
}

NAMES = {
    "compatible-soave": {
        "name": "COMPATIBLE SOAVE",
        "name_ar": "COMPATIBLE SOAVE",
    },
    "compatible-ethiopia": {
        "name": "COMPATIBLE ETHIOPIA",
        "name_ar": "COMPATIBLE ETHIOPIA",
    },
    "caffitaly-corposo": {
        "name": "Caffitaly Croposo",
        "name_ar": "Caffitaly Croposo",
    },
    "caffitaly-vigoroso": {
        "name": "Caffitaly Virgoso",
        "name_ar": "Caffitaly Virgoso",
    },
    "caffitaly-decaffeinato": {
        "name": "Caffitaly Decaffeinato",
        "name_ar": "Caffitaly Decaffeinato",
    },
    "caffitaly-cremoso": {
        "name": "Caffitaly Cremoso",
        "name_ar": "Caffitaly Cremoso",
    },
    "compatible-deca": {
        "name": "COMPATIBLE Deca",
        "name_ar": "COMPATIBLE Deca",
    },
    "caffitaly-intenso": {
        "name": "Caffitaly Intenso",
        "name_ar": "Caffitaly Intenso",
    },
    "compatible-vivace": {
        "name": "COMPATIBLE Vivace",
        "name_ar": "COMPATIBLE Vivace",
    },
}


def apply_order(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    for slug, order in CAFFITALY_ORDER.items():
        Product.objects.filter(slug=slug).update(display_order=order)
    for slug, names in NAMES.items():
        Product.objects.filter(slug=slug).update(**names)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0009_rio_house_order"),
    ]

    operations = [
        migrations.RunPython(apply_order, noop),
    ]
