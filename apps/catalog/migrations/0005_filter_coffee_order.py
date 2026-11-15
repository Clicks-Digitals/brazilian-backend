from django.db import migrations


FILTER_ORDER = {
    "filter-coffee-original": 1,
    "filter-coffee-bag": 2,
    "filter-coffee-peru": 3,
    "filter-coffee-colombian": 4,
    "filter-coffee-ethiopian": 5,
    "filter-coffee-organic": 6,
    "filter-coffee-macadamia": 7,
    "filter-coffee-kenyan": 8,
    "filter-coffee-vanilla": 9,
    "filter-coffee-hazelnut": 10,
    "filter-coffee-salted-caramel": 11,
    "filter-coffee-vanilla-hazelnut": 12,
    "filter-coffee-mastic": 13,
    "filter-coffee-chocolate": 14,
    "filter-coffee-decaf": 15,
}

NAME_AR = {
    "filter-coffee-original": "قهوة الفلتر الأصلية",
    "filter-coffee-bag": "قهوة فلتر الأصلية كيس",
    "filter-coffee-peru": "قهوة فلتر بيرو",
    "filter-coffee-colombian": "قهوة فلتر كولومبية",
    "filter-coffee-ethiopian": "قهوة فلتر أثيوبيية",
    "filter-coffee-organic": "قهوة فلتر عضوية",
    "filter-coffee-macadamia": "قهوة فلتر بنكهة المكاديميا",
    "filter-coffee-kenyan": "قهوة فلتر كينية",
    "filter-coffee-vanilla": "قهوة فلتر بنكهة الفانيلا",
    "filter-coffee-hazelnut": "قهوة فلتر بنكهة البندق",
    "filter-coffee-salted-caramel": "قهوة فلتر بنكهة الكراميل",
    "filter-coffee-vanilla-hazelnut": "قهوة فلتر بنكهة البندق والفانيلا",
    "filter-coffee-mastic": "قهوة فلتر بنكهة المستكة",
    "filter-coffee-chocolate": "قهوة فلتر بنكهة الشوكولاتة",
}


def apply_order(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    for slug, order in FILTER_ORDER.items():
        Product.objects.filter(slug=slug).update(display_order=order)
    for slug, name_ar in NAME_AR.items():
        Product.objects.filter(slug=slug).update(name_ar=name_ar)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0004_turkish_coffee_app_range"),
    ]

    operations = [
        migrations.RunPython(apply_order, noop),
    ]
