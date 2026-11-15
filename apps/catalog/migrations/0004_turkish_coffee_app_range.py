from django.db import migrations


TURKISH_ORDER = {
    "turkish-coffee-jordanian-blend": 1,
    "turkish-coffee-jordanian-blend-bag": 2,
    "french-coffee-macadamia": 3,
    "turkish-coffee-jordanian-blend-sachets": 4,
    "turkish-coffee-decaf": 5,
    "turkish-coffee-no-cardamom": 6,
    "turkish-coffee-colombian": 7,
    "turkish-coffee-ethiopian": 8,
    "turkish-coffee-indian": 9,
    "turkish-coffee-kenyan": 10,
    "turkish-coffee-jordanian-blend-dark": 11,
    "turkish-coffee-peru": 12,
    "turkish-coffee-light": 13,
    "turkish-coffee-jordanian-blend-light": 14,
    "turkish-coffee-dark": 15,
    "turkish-coffee-medium": 16,
    "turkish-coffee-medium-bag": 17,
    "turkish-coffee-light-bag": 18,
    "turkish-coffee-decaf-bag": 19,
    "turkish-coffee-dark-bag": 20,
    "french-coffee": 21,
    "ottoman-coffee": 22,
    "turkish-coffee-macadamia": 23,
    "french-coffee-hazelnut": 24,
    "turkish-coffee-vanilla": 25,
    "turkish-coffee-hazelnut": 26,
    "turkish-coffee-caramel": 27,
    "turkish-coffee-hazelnut-vanilla": 28,
    "turkish-coffee-mastic": 29,
    "turkish-coffee-chocolate": 30,
    "turkish-coffee-sachet": 31,
}


def apply_order(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    for slug, order in TURKISH_ORDER.items():
        Product.objects.filter(slug=slug).update(display_order=order)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0003_reorder_turkish_coffee"),
    ]

    operations = [
        migrations.RunPython(apply_order, noop),
    ]
