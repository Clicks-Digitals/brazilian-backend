from django.db import migrations


ARABIC_ORDER = {
    "arabic-coffee-sachet": 1,
    "arabic-coffee-10-sachets": 2,
    "saudi-coffee-sachet": 3,
    "saudi-coffee-10-sachets": 4,
    "saudi-coffee-bag": 5,
    "arabic-coffee-bag": 6,
}

NAME_AR = {
    "arabic-coffee-sachet": "قهوة عربية مغلف (سريعه التحضير)",
    "arabic-coffee-10-sachets": "قهوة عربية (سريعه التحضير)",
    "saudi-coffee-sachet": "قهوة سعودية مغلف (سريعه التحضير)",
    "saudi-coffee-10-sachets": "قهوة سعودية (سريعه التحضير) 10 مغلف",
    "saudi-coffee-bag": "قهوة سعودية",
    "arabic-coffee-bag": "قهوة عربية",
}


def apply_order(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    for slug, order in ARABIC_ORDER.items():
        Product.objects.filter(slug=slug).update(display_order=order)
    for slug, name_ar in NAME_AR.items():
        Product.objects.filter(slug=slug).update(name_ar=name_ar)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0007_espresso_order"),
    ]

    operations = [
        migrations.RunPython(apply_order, noop),
    ]
