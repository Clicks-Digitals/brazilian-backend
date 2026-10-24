from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.cms.models import Article
from apps.cms.services import sanitize_html
from apps.core.testing import jpeg_file, make_product, make_user, make_variant


class ArticleVisibilityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        author = make_user("writer@test.com", staff=True)
        self.published = Article.objects.create(
            title="Heritage mill",
            slug="heritage-mill",
            excerpt="From 1955.",
            content="<p>Safe</p><script>alert(1)</script>",
            status=Article.Status.PUBLISHED,
            published_at=timezone.now(),
            author=author,
        )
        self.draft = Article.objects.create(
            title="Draft piece",
            slug="draft-piece",
            excerpt="Hidden",
            content="<p>Nope</p>",
            status=Article.Status.DRAFT,
            author=author,
        )

    def test_unpublished_articles_are_hidden(self):
        listing = self.client.get("/api/v1/articles/")
        self.assertEqual(listing.status_code, 200)
        slugs = [row["slug"] for row in listing.data["results"]]
        self.assertIn("heritage-mill", slugs)
        self.assertNotIn("draft-piece", slugs)
        hidden = self.client.get("/api/v1/articles/draft-piece/")
        self.assertEqual(hidden.status_code, 404)

    def test_article_content_is_sanitized(self):
        self.assertNotIn("<script>", sanitize_html(self.published.content))
        detail = self.client.get("/api/v1/articles/heritage-mill/")
        self.assertEqual(detail.status_code, 200)
        self.assertNotIn("<script>", detail.data["content"])

    def test_article_related_products_are_nested(self):
        from apps.catalog.models import ProductImage

        product = make_product()
        make_variant(product)
        ProductImage.objects.create(product=product, image=jpeg_file("related.jpg"), is_primary=True)
        extras = [
            make_product(slug="espresso-medium", sku="BCH-ESP-MED", name="Espresso Medium"),
            make_product(slug="filter-coffee-original", sku="BCH-FIL-ORG", name="Original Filter Coffee"),
        ]
        for extra in extras:
            make_variant(extra, sku=f"{extra.sku}-V")
            ProductImage.objects.create(product=extra, image=jpeg_file(f"{extra.slug}.jpg"), is_primary=True)
        self.published.related_products.add(product)

        detail = self.client.get("/api/v1/articles/heritage-mill/")
        self.assertEqual(detail.status_code, 200)
        related = detail.data["related_products"]
        self.assertEqual(len(related), 3)
        self.assertEqual(related[0]["slug"], "turkish-coffee-medium")
        self.assertTrue(related[0]["primary_image"])
        self.assertTrue(related[0]["price"])


class ContactTests(TestCase):
    def test_contact_message_is_stored(self):
        client = APIClient()
        response = client.post(
            "/api/v1/contact/",
            {
                "name": "Sara Haddad",
                "email": "sara@example.com",
                "phone": "0790000000",
                "message": "Do you roast a light Turkish for home cezve?",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        from apps.cms.models import ContactMessage

        saved = ContactMessage.objects.get()
        self.assertEqual(saved.email, "sara@example.com")
        self.assertIn("Turkish", saved.message)


class StorefrontTests(TestCase):
    def test_storefront_and_settings(self):
        from apps.cms.models import StoreSetting

        StoreSetting.objects.create(
            key="store",
            value={"store_name": "Brazilian Coffee House", "currency": "JOD"},
        )
        client = APIClient()
        storefront = client.get("/api/v1/storefront/")
        self.assertEqual(storefront.status_code, 200)
        self.assertIn("announcements", storefront.data)
        self.assertIn("hero_banners", storefront.data)
        self.assertIn("settings", storefront.data)
        settings = client.get("/api/v1/settings/")
        self.assertEqual(settings.data["store_name"], "Brazilian Coffee House")
