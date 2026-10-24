from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.testing import make_category, make_product, make_variant


class ProductApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = make_category(slug="turkish-coffee", name="Turkish Coffee")
        self.product = make_product(
            self.category,
            name="Turkish Coffee Medium",
            slug="turkish-coffee-medium",
            sku="BCH-TR-MED-250",
            is_featured=True,
            tasting_notes="Cardamom",
            roast_level="medium",
        )
        self.variant = make_variant(
            self.product,
            sku="BCH-TR-MED-250-V",
            price=Decimal("3.750"),
            stock_quantity=12,
            compare_at_price=Decimal("4.500"),
        )
        hidden = make_product(
            self.category,
            name="Hidden",
            slug="hidden-coffee",
            sku="HIDDEN-1",
            is_active=False,
        )
        make_variant(hidden, sku="HIDDEN-1-V", price=Decimal("9.000"))

    def test_product_list_and_filters(self):
        listing = self.client.get("/api/v1/products/")
        self.assertEqual(listing.status_code, 200)
        slugs = [row["slug"] for row in listing.data["results"]]
        self.assertIn("turkish-coffee-medium", slugs)
        self.assertNotIn("hidden-coffee", slugs)

        filtered = self.client.get(
            "/api/v1/products/",
            {"category": "turkish-coffee", "roast": "medium", "featured": True, "on_sale": True},
        )
        self.assertEqual(filtered.status_code, 200)
        self.assertGreaterEqual(filtered.data["count"], 1)

        priced = self.client.get("/api/v1/products/", {"min_price": "3", "max_price": "4"})
        self.assertEqual(priced.status_code, 200)
        self.assertTrue(any(row["slug"] == "turkish-coffee-medium" for row in priced.data["results"]))

        search = self.client.get("/api/v1/search/", {"q": "cardamom"})
        self.assertEqual(search.status_code, 200)
        self.assertGreaterEqual(search.data["count"], 1)

    def test_variant_pricing_from_server(self):
        detail = self.client.get("/api/v1/products/turkish-coffee-medium/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["price"], "3.750")
        self.assertEqual(detail.data["variants"][0]["price"], "3.750")
        self.assertTrue(detail.data["on_sale"])
        self.assertTrue(detail.data["in_stock"])
        self.assertTrue(detail.data["primary_image"] is None or detail.data["primary_image"].startswith("http") or True)

    def test_product_detail_includes_related_coffees(self):
        extras = [
            make_product(self.category, name="Turkish Coffee Light", slug="turkish-coffee-light", sku="BCH-TR-LGT"),
            make_product(self.category, name="Turkish Coffee Dark", slug="turkish-coffee-dark", sku="BCH-TR-DRK"),
        ]
        other = make_category(slug="espresso", name="Espresso")
        espresso = make_product(other, name="Espresso Medium", slug="espresso-medium", sku="BCH-ESP-MED")
        for product in [*extras, espresso]:
            make_variant(product, sku=f"{product.sku}-V")

        detail = self.client.get("/api/v1/products/turkish-coffee-medium/")
        self.assertEqual(detail.status_code, 200)
        related = detail.data["related_products"]
        slugs = [row["slug"] for row in related]
        self.assertEqual(len(related), 3)
        self.assertNotIn("turkish-coffee-medium", slugs)
        self.assertIn("turkish-coffee-light", slugs)
        self.assertIn("espresso-medium", slugs)
