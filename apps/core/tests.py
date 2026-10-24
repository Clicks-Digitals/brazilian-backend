from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.testing import auth_client, jpeg_file, make_product, make_user, make_variant


class HealthTests(TestCase):
    def test_health(self):
        response = APIClient().get("/api/v1/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ok")


class ImageUploadValidationTests(TestCase):
    def setUp(self):
        self.user = make_user(
            "staff@test.com",
            staff=True,
            codes=["products.view", "products.create", "products.edit"],
        )
        self.client = auth_client(self.user)
        self.product = make_product()
        make_variant(self.product, sku="IMG-VAR-1")

    def test_image_upload_rejects_executable(self):
        payload = {
            "image": SimpleUploadedFile(
                "malware.exe",
                b"MZ\x90\x00this is not an image",
                content_type="application/x-msdownload",
            )
        }
        response = self.client.post(
            f"/api/v1/admin/products/{self.product.pk}/images/",
            payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

    def test_image_upload_rejects_spoofed_jpeg(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        fake = SimpleUploadedFile(
            "photo.jpg",
            b"#!/usr/bin/python\nprint('nope')\n",
            content_type="image/jpeg",
        )
        response = self.client.post(
            f"/api/v1/admin/products/{self.product.pk}/images/",
            {"image": fake},
            format="multipart",
        )
        self.assertEqual(response.status_code, 400)

    def test_image_upload_accepts_jpeg(self):
        response = self.client.post(
            f"/api/v1/admin/products/{self.product.pk}/images/",
            {"image": jpeg_file(), "alt_text": "Tin", "is_primary": True},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["url"].startswith("http"))
