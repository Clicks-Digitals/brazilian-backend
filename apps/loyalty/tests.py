from django.test import TestCase, override_settings

from apps.core.testing import auth_client, make_user
from apps.loyalty.services import DisabledAdapter, MockAdapter, get_adapter, loyalty_payload


class LoyaltyAdapterTests(TestCase):
    def test_adapter_disabled_by_default(self):
        user = make_user("loyal@example.com")
        client = auth_client(user)
        response = client.get("/api/v1/account/loyalty/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["configured"])
        self.assertIn(response.data["adapter"], {"disabled", "mock"})
        self.assertNotIn("balance", response.data)

    @override_settings(LOYALTY_ENABLED=False, LOYALTY_ADAPTER="disabled")
    def test_disabled_adapter_instance(self):
        adapter = get_adapter()
        self.assertIsInstance(adapter, DisabledAdapter)
        payload = loyalty_payload()
        self.assertEqual(payload, {"configured": False, "adapter": "disabled"})

    @override_settings(LOYALTY_ENABLED=False, LOYALTY_ADAPTER="mock")
    def test_mock_adapter_is_labelled_and_has_no_balance(self):
        adapter = get_adapter()
        self.assertIsInstance(adapter, MockAdapter)
        payload = adapter.get_status()
        self.assertFalse(payload["configured"])
        self.assertEqual(payload["adapter"], "mock")
        self.assertNotIn("points", payload)
        self.assertNotIn("balance", payload)

    @override_settings(
        LOYALTY_ENABLED=True,
        LOYALTY_ADAPTER="clicks",
        LOYALTY_API_BASE_URL="",
        LOYALTY_API_KEY="",
        LOYALTY_API_SECRET="",
    )
    def test_enabled_without_credentials_fails_gracefully(self):
        payload = loyalty_payload()
        self.assertFalse(payload["configured"])
        self.assertEqual(payload["adapter"], "disabled")
