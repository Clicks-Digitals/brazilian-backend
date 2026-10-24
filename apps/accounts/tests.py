from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient

from apps.accounts.models import CustomerAddress, User
from apps.core.testing import auth_client, make_user


class AuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_and_login(self):
        register = self.client.post(
            "/api/v1/auth/register/",
            {
                "email": "new.customer@example.com",
                "password": "HouseRoast!2345",
                "first_name": "New",
                "last_name": "Guest",
                "phone": "0791112233",
            },
            format="json",
        )
        self.assertEqual(register.status_code, 201, register.data)
        self.assertIn("access", register.data)
        self.assertEqual(register.data["user"]["email"], "new.customer@example.com")

        login = self.client.post(
            "/api/v1/auth/login/",
            {"email": "new.customer@example.com", "password": "HouseRoast!2345"},
            format="json",
        )
        self.assertEqual(login.status_code, 200, login.data)
        self.assertIn("refresh", login.data)

        staff = make_user("staff.profile@test.com", staff=True, codes=["dashboard.view"])
        staff_client = auth_client(staff)
        me = staff_client.get("/api/v1/account/")
        self.assertEqual(me.status_code, 200)
        self.assertTrue(me.data["is_staff"])
        self.assertIn("dashboard.view", me.data["permissions"])

    def test_logout_blacklists_refresh(self):
        make_user("out@example.com", "Customer12345!")
        login = self.client.post(
            "/api/v1/auth/login/",
            {"email": "out@example.com", "password": "Customer12345!"},
            format="json",
        )
        refresh = login.data["refresh"]
        logout = self.client.post("/api/v1/auth/logout/", {"refresh": refresh}, format="json")
        self.assertEqual(logout.status_code, 200)
        again = self.client.post("/api/v1/auth/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(again.status_code, 401)

    def test_password_reset(self):
        user = make_user("resetme@example.com", "Customer12345!")
        forgot = self.client.post(
            "/api/v1/auth/forgot-password/", {"email": user.email}, format="json"
        )
        self.assertEqual(forgot.status_code, 200)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset = self.client.post(
            "/api/v1/auth/reset-password/",
            {"uid": uid, "token": token, "password": "NewPass12345!"},
            format="json",
        )
        self.assertEqual(reset.status_code, 200, reset.data)
        login = self.client.post(
            "/api/v1/auth/login/",
            {"email": user.email, "password": "NewPass12345!"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)

    def test_admin_login_rejects_customer(self):
        make_user("cust@example.com", "Customer12345!")
        response = self.client.post(
            "/api/v1/admin/auth/login/",
            {"email": "cust@example.com", "password": "Customer12345!"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)


class OwnershipTests(TestCase):
    def test_address_and_profile_are_owner_scoped(self):
        alice = make_user("alice@example.com")
        bob = make_user("bob@example.com")
        address = CustomerAddress.objects.create(
            user=alice,
            full_name="Alice",
            phone="0790000001",
            line1="Street 1",
            city="Amman",
        )
        bob_client = auth_client(bob)
        response = bob_client.patch(
            f"/api/v1/account/addresses/{address.pk}/",
            {"city": "Irbid"},
            format="json",
        )
        self.assertIn(response.status_code, {403, 404})
        alice_client = auth_client(alice)
        mine = alice_client.get("/api/v1/account/addresses/")
        self.assertEqual(mine.status_code, 200)
        self.assertEqual(len(mine.data), 1)


class PermissionTests(TestCase):
    def test_staff_without_permission_gets_403(self):
        staff = make_user("limited@test.com", staff=True, codes=["dashboard.view"])
        client = auth_client(staff)
        response = client.post(
            "/api/v1/admin/products/",
            {
                "name": "Nope",
                "sku": "NOPE-1",
                "slug": "nope",
                "category": 1,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["error"]["code"], "permission_denied")
