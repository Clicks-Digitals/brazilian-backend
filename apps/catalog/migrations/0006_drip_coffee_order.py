from django.db import migrations


DRIP_ORDER = {
    "drip-coffee-original": 1,
    "drip-coffee-decaf": 2,
    "drip-coffee-hazelnut": 3,
    "drip-coffee-macadamia": 4,
}

NAME_AR = {
    "drip-coffee-original": "درب كوفي - أوريجينال",
    "drip-coffee-decaf": "درب كوفي - بدون كافيين",
    "drip-coffee-hazelnut": "درب كوفي - بالبندق",
    "drip-coffee-macadamia": "درب كوفي - مكاديميا",
}


def apply_order(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    for slug, order in DRIP_ORDER.items():
        Product.objects.filter(slug=slug).update(display_order=order)
    for slug, name_ar in NAME_AR.items():
        Product.objects.filter(slug=slug).update(name_ar=name_ar)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0005_filter_coffee_order"),
    ]

    operations = [
        migrations.RunPython(apply_order, noop),
    ]
