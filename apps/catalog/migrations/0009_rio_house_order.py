from django.db import migrations


RIO_ORDER = {
    "rio-house-creamer-small": 1,
    "rio-house-creamer": 2,
    "rio-house-gold": 3,
    "rio-house-black-gar": 4,
    "rio-house-2-in-1-bag": 5,
    "rio-house-3-in-1-bag": 6,
    "rio-house-hazelnut-cappuccino-1kg": 7,
    "rio-house-3-in-1-1kg": 8,
    "rio-house-caramel-cappuccino-1kg": 9,
    "rio-house-hot-chocolate-1kg": 10,
    "rio-house-3-in-1": 11,
    "rio-house-black-500g": 12,
    "rio-house-black": 13,
    "rio-house-2-in-1": 14,
    "rio-house-mocha": 15,
    "rio-house-hot-chocolate": 16,
    "rio-house-lentil": 17,
    "rio-house-milk-ginger": 18,
    "rio-house-mix": 19,
    "rio-house-hazelnut-cappuccino": 20,
    "rio-house-caramel-cappuccino": 21,
    "rio-house-chai-karak": 22,
    "rio-house-salep": 23,
}

NAMES = {
    "rio-house-creamer-small": {
        "name": "Rio House Whitener",
        "name_ar": "مبيض ريوهاوس",
    },
    "rio-house-creamer": {
        "name": "Rio House Whitener Large",
        "name_ar": "مبيض ريوهاوس",
    },
    "rio-house-gold": {
        "name": "Rio House Gold",
        "name_ar": "ريو هاوس جولد",
    },
    "rio-house-black-gar": {
        "name": "Rio House Black Jar",
        "name_ar": "ريو هاوس بلاك علبة",
    },
    "rio-house-2-in-1-bag": {
        "name": "2 IN 1 bag 30 sachet",
        "name_ar": "2 IN 1 bag 30 sachet",
    },
    "rio-house-3-in-1-bag": {
        "name": "3 IN 1 bag 30 sachet",
        "name_ar": "3 IN 1 bag 30 sachet",
    },
    "rio-house-hazelnut-cappuccino-1kg": {
        "name": "Hazelnut cappuccino 1 kilo",
        "name_ar": "Hazelnut cappuccino 1 kilo",
    },
    "rio-house-3-in-1-1kg": {
        "name": "Rio House 3 in 1 / 1 kilo",
        "name_ar": "Rio house 3 in 1 / 1kilo",
    },
    "rio-house-caramel-cappuccino-1kg": {
        "name": "Caramel cappuccino 1 kg",
        "name_ar": "Caramel cappuccino 1 kg",
    },
    "rio-house-hot-chocolate-1kg": {
        "name": "Hot chocolate 1 kg",
        "name_ar": "Hot chocolate 1 kg",
    },
    "rio-house-3-in-1": {
        "name": "Rio House 3 in 1",
        "name_ar": "ريو هاوس ٣في١",
    },
    "rio-house-black-500g": {
        "name": "Rio House Black 500g",
        "name_ar": "Rio house Black 500g",
    },
    "rio-house-black": {
        "name": "Rio House Black",
        "name_ar": "ريو هاوس بلاك",
    },
    "rio-house-2-in-1": {
        "name": "Rio House 2 in 1",
        "name_ar": "ريو هاوس ٢ في ١",
    },
    "rio-house-mocha": {
        "name": "Rio House Mocha",
        "name_ar": "ريو هاوس موكا",
    },
    "rio-house-hot-chocolate": {
        "name": "Rio House Hot Chocolate",
        "name_ar": "ريو هاوس شوكولاته ساخنة",
    },
    "rio-house-lentil": {
        "name": "Rio House Lentil",
        "name_ar": "ريو هاوس عدس",
    },
    "rio-house-milk-ginger": {
        "name": "Rio House Milk & Ginger",
        "name_ar": "ريو هاوس حليب وزنجبيل",
    },
    "rio-house-mix": {
        "name": "Rio House Mix",
        "name_ar": "ريو هاوس مكس",
    },
}


def apply_order(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    for slug, order in RIO_ORDER.items():
        Product.objects.filter(slug=slug).update(display_order=order)
    for slug, names in NAMES.items():
        Product.objects.filter(slug=slug).update(**names)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0008_arabic_coffee_order"),
    ]

    operations = [
        migrations.RunPython(apply_order, noop),
    ]
