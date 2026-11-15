from django.db import migrations


MACHINE_ORDER = {
    "caffitaly-s33": 1,
    "caffitaly-s36": 2,
    "caffitaly-s18": 3,
    "caffitaly-s16": 4,
    "caffitaly-s22": 5,
    "caffitaly-s24": 6,
    "caffitaly-s27": 7,
}

NAMES = {
    "caffitaly-s33": {
        "name": "Caffitaly S33",
        "name_ar": "كافيتالي S33",
    },
    "caffitaly-s36": {
        "name": "Caffitaly S36",
        "name_ar": "كافيتالي S36",
    },
    "caffitaly-s18": {
        "name": "Caffitaly S18",
        "name_ar": "كافيتالي S18",
    },
    "caffitaly-s16": {
        "name": "Caffitaly S16",
        "name_ar": "كافيتالي S16",
    },
    "caffitaly-s22": {
        "name": "Caffitaly S22",
        "name_ar": "كافيتالي S22",
    },
    "caffitaly-s24": {
        "name": "Caffitaly S24",
        "name_ar": "كافيتالي S24",
    },
    "caffitaly-s27": {
        "name": "Caffitaly S27",
        "name_ar": "كافيتالي S27",
    },
}


def apply_order(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    for slug, order in MACHINE_ORDER.items():
        Product.objects.filter(slug=slug).update(display_order=order)
    for slug, names in NAMES.items():
        Product.objects.filter(slug=slug).update(**names)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0010_caffitaly_capsules_order"),
    ]

    operations = [
        migrations.RunPython(apply_order, noop),
    ]
