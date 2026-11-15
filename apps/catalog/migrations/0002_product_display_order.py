from django.db import migrations, models


TURKISH_ORDER = {
    "turkish-coffee-jordanian-blend-bag": 1,
    "french-coffee-macadamia": 2,
    "turkish-coffee-decaf": 3,
    "turkish-coffee-ethiopian": 4,
    "turkish-coffee-colombian": 5,
    "turkish-coffee-kenyan": 6,
    "turkish-coffee-indian": 7,
    "turkish-coffee-peru": 8,
    "turkish-coffee-jordanian-blend": 9,
    "turkish-coffee-light": 10,
    "turkish-coffee-medium": 11,
    "turkish-coffee-dark": 12,
    "ottoman-coffee": 13,
    "french-coffee": 14,
    "french-coffee-hazelnut": 15,
    "turkish-coffee-macadamia": 16,
    "turkish-coffee-hazelnut": 17,
    "turkish-coffee-vanilla": 18,
    "turkish-coffee-hazelnut-vanilla": 19,
    "turkish-coffee-caramel": 20,
    "turkish-coffee-chocolate": 21,
    "turkish-coffee-mastic": 22,
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
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="display_order",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(fields=["category", "display_order"], name="catalog_prod_cat_order_idx"),
        ),
        migrations.AlterModelOptions(
            name="product",
            options={"ordering": ["display_order", "name"]},
        ),
        migrations.RunPython(set_turkish_order, noop),
    ]
