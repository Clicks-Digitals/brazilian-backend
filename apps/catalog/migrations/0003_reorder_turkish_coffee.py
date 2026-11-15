from django.db import migrations


TURKISH_ORDER = {
    "turkish-coffee-jordanian-blend": 1,
    "turkish-coffee-jordanian-blend-bag": 2,
    "french-coffee-macadamia": 3,
    "turkish-coffee-decaf": 4,
    "turkish-coffee-colombian": 5,
    "turkish-coffee-ethiopian": 6,
    "turkish-coffee-indian": 7,
    "turkish-coffee-kenyan": 8,
    "turkish-coffee-peru": 9,
    "turkish-coffee-light": 10,
    "turkish-coffee-dark": 11,
    "turkish-coffee-medium": 12,
    "french-coffee": 13,
    "ottoman-coffee": 14,
    "turkish-coffee-macadamia": 15,
    "french-coffee-hazelnut": 16,
    "turkish-coffee-vanilla": 17,
    "turkish-coffee-hazelnut": 18,
    "turkish-coffee-caramel": 19,
    "turkish-coffee-hazelnut-vanilla": 20,
    "turkish-coffee-mastic": 21,
    "turkish-coffee-chocolate": 22,
    "turkish-coffee-sachet": 23,
}


def set_turkish_order(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    for slug, order in TURKISH_ORDER.items():
        Product.objects.filter(slug=slug).update(display_order=order)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0002_product_display_order"),
    ]

    operations = [
        migrations.RunPython(set_turkish_order, noop),
    ]
