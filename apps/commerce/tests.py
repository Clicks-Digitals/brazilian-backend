from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.commerce.models import Discount, Order
from apps.core.testing import auth_client, make_product, make_user, make_variant
from apps.core.utils import money


class CartCheckoutTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.product = make_product()
        self.variant = make_variant(
            self.product,
            sku="CART-VAR-1",
            price=Decimal("12.000"),
            stock_quantity=5,
        )
        self.customer = {
            "email": "buyer@example.com",
            "first_name": "Buyer",
            "last_name": "Guest",
            "phone": "0792223344",
        }
        self.address = {
            "line1": "1 Rainbow Street",
            "city": "Amman",
            "area": "Jabal Amman",
            "country": "Jordan",
        }

    def _add_to_cart(self, quantity=1, variant=None):
        variant = variant or self.variant
        response = self.client.post(
            "/api/v1/cart/",
            {"variant_id": variant.id, "quantity": quantity},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.client.credentials(HTTP_X_CART_TOKEN=response.data["token"])
        return response

    def test_cart_add_and_checkout_totals(self):
        cart = self._add_to_cart(2)
        self.assertEqual(cart.data["items"][0]["unit_price"], "12.000")
        self.assertEqual(cart.data["subtotal"], "24.000")
        self.assertEqual(cart.data["delivery_fee"], "2.000")
        self.assertEqual(cart.data["total"], "26.000")

        Discount.objects.create(
            code="WELCOME10",
            name="Welcome 10%",
            discount_type=Discount.DiscountType.PERCENTAGE,
            value=Decimal("10.000"),
            min_order_amount=Decimal("10.000"),
            is_active=True,
        )
        apply = self.client.post("/api/v1/cart/", {"discount_code": "WELCOME10"}, format="json")
        self.assertEqual(apply.status_code, 200, apply.data)
        self.assertEqual(apply.data["discount_amount"], "2.400")
        self.assertEqual(apply.data["total"], "23.600")

        key = str(uuid4())
        checkout = self.client.post(
            "/api/v1/checkout/",
            {
                "cart_token": apply.data["token"],
                "customer": self.customer,
                "address": self.address,
                "payment_method": "cod",
                "discount_code": "WELCOME10",
                "idempotency_key": key,
            },
            format="json",
        )
        self.assertEqual(checkout.status_code, 201, checkout.data)
        self.assertEqual(checkout.data["payment_status"], "unpaid")
        self.assertEqual(checkout.data["status"], "pending")
        self.assertEqual(checkout.data["payment_method"], "cod")
        self.assertEqual(checkout.data["total"], "23.600")
        self.assertTrue(checkout.data["order_number"].startswith("BCH-"))
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 3)

        duplicate = self.client.post(
            "/api/v1/checkout/",
            {
                "cart_token": apply.data["token"],
                "customer": self.customer,
                "address": self.address,
                "payment_method": "cod",
                "idempotency_key": key,
            },
            format="json",
        )
        self.assertIn(duplicate.status_code, {200, 201})
        self.assertEqual(duplicate.data["order_number"], checkout.data["order_number"])
        self.assertEqual(Order.objects.filter(idempotency_key=key).count(), 1)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock_quantity, 3)

    def test_stock_validation(self):
        response = self.client.post(
            "/api/v1/cart/",
            {"variant_id": self.variant.id, "quantity": 9},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "out_of_stock")

    def test_discount_invalid_and_expired(self):
        self._add_to_cart(1)
        missing = self.client.post(
            "/api/v1/discounts/validate/", {"code": "NOPE"}, format="json"
        )
        self.assertEqual(missing.status_code, 400)
        expired = Discount.objects.create(
            code="OLD10",
            name="Old",
            discount_type=Discount.DiscountType.PERCENTAGE,
            value=Decimal("10.000"),
            min_order_amount=Decimal("1.000"),
            is_active=True,
            ends_at=timezone.now() - timedelta(days=1),
        )
        response = self.client.post(
            "/api/v1/discounts/validate/", {"code": "OLD10"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "discount_expired")
        self.assertTrue(expired.pk)

    def test_order_status_and_payment_independence(self):
        staff = make_user(
            "orders-admin@test.com",
            staff=True,
            codes=["orders.view", "orders.edit", "dashboard.view"],
        )
        self._add_to_cart(1)
        cart = self.client.get("/api/v1/cart/")
        checkout = self.client.post(
            "/api/v1/checkout/",
            {
                "cart_token": cart.data["token"],
                "customer": self.customer,
                "address": self.address,
                "payment_method": "cod",
                "idempotency_key": str(uuid4()),
            },
            format="json",
        )
        self.assertEqual(checkout.status_code, 201, checkout.data)
        order_id = checkout.data["id"]
        admin = auth_client(staff)
        confirmed = admin.post(
            f"/api/v1/admin/orders/{order_id}/status/",
            {"status": "confirmed", "note": "Called customer"},
            format="json",
        )
        self.assertEqual(confirmed.status_code, 200, confirmed.data)
        self.assertEqual(confirmed.data["status"], "confirmed")
        self.assertEqual(confirmed.data["payment_status"], "unpaid")
        paid = admin.post(
            f"/api/v1/admin/orders/{order_id}/payment/",
            {"payment_status": "paid"},
            format="json",
        )
        self.assertEqual(paid.status_code, 200)
        self.assertEqual(paid.data["payment_status"], "paid")
        self.assertEqual(paid.data["status"], "confirmed")

    def test_dashboard_uses_real_totals(self):
        staff = make_user("analyst@test.com", staff=True, codes=["dashboard.view"])
        self._add_to_cart(1)
        cart = self.client.get("/api/v1/cart/")
        checkout = self.client.post(
            "/api/v1/checkout/",
            {
                "cart_token": cart.data["token"],
                "customer": self.customer,
                "address": self.address,
                "payment_method": "cod",
                "idempotency_key": str(uuid4()),
            },
            format="json",
        )
        self.assertEqual(checkout.status_code, 201, checkout.data)
        expected = money(checkout.data["total"])
        admin = auth_client(staff)
        dash = admin.get("/api/v1/admin/dashboard/")
        self.assertEqual(dash.status_code, 200, dash.data)
        self.assertEqual(money(dash.data["sales"]["unpaid_cod"]), expected)
        self.assertEqual(money(dash.data["sales"]["total"]), expected)
        self.assertNotEqual(dash.data["sales"]["total"], "99999.000")
        self.assertGreaterEqual(dash.data["orders_by_status"]["pending"], 1)


class InventoryLockTests(TransactionTestCase):
    def test_second_checkout_cannot_oversell(self):
        product = make_product(slug="lock-coffee", sku="LOCK-1")
        variant = make_variant(product, sku="LOCK-1-V", price=Decimal("5.000"), stock_quantity=1)
        address = {"line1": "A", "city": "Amman"}

        def make_cart():
            client = APIClient()
            added = client.post(
                "/api/v1/cart/",
                {"variant_id": variant.id, "quantity": 1},
                format="json",
            )
            self.assertEqual(added.status_code, 200, added.data)
            client.credentials(HTTP_X_CART_TOKEN=added.data["token"])
            return client, added.data["token"]

        client_a, token_a = make_cart()
        client_b, token_b = make_cart()

        def place(client, token, email):
            return client.post(
                "/api/v1/checkout/",
                {
                    "cart_token": token,
                    "customer": {
                        "email": email,
                        "first_name": "One",
                        "last_name": "Buyer",
                        "phone": "0790001111",
                    },
                    "address": address,
                    "payment_method": "cod",
                    "idempotency_key": str(uuid4()),
                },
                format="json",
            )

        first = place(client_a, token_a, "one@example.com")
        second = place(client_b, token_b, "two@example.com")
        codes = sorted([first.status_code, second.status_code])
        self.assertEqual(codes, [201, 400], [first.data, second.data])
        variant.refresh_from_db()
        self.assertEqual(variant.stock_quantity, 0)
        self.assertEqual(Order.objects.count(), 1)
