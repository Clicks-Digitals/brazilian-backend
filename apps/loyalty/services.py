from abc import ABC, abstractmethod

from django.conf import settings


class LoyaltyAdapter(ABC):
    name = "base"

    @abstractmethod
    def is_configured(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_status(self, user=None) -> dict:
        raise NotImplementedError


class DisabledAdapter(LoyaltyAdapter):
    name = "disabled"

    def is_configured(self) -> bool:
        return False

    def get_status(self, user=None) -> dict:
        return {"configured": False, "adapter": self.name}


class MockAdapter(LoyaltyAdapter):
    """Labelled mock — never invents live loyalty balances."""

    name = "mock"

    def is_configured(self) -> bool:
        return False

    def get_status(self, user=None) -> dict:
        return {
            "configured": False,
            "adapter": self.name,
            "note": "Mock adapter only. No live loyalty balances are available.",
        }


def _has_real_credentials() -> bool:
    return bool(
        getattr(settings, "LOYALTY_API_BASE_URL", "")
        and getattr(settings, "LOYALTY_API_KEY", "")
        and getattr(settings, "LOYALTY_API_SECRET", "")
    )


def get_adapter() -> LoyaltyAdapter:
    if not getattr(settings, "LOYALTY_ENABLED", False):
        adapter_name = (getattr(settings, "LOYALTY_ADAPTER", "disabled") or "disabled").lower()
        if adapter_name == "mock":
            return MockAdapter()
        return DisabledAdapter()
    if not _has_real_credentials():
        return DisabledAdapter()
    # Credentials may exist for a future provider. We still do not fabricate balances
    # or claim a live Clicks (or other) API integration.
    return DisabledAdapter()


def loyalty_payload(user=None) -> dict:
    adapter = get_adapter()
    payload = adapter.get_status(user)
    if getattr(settings, "LOYALTY_ENABLED", False) and _has_real_credentials():
        payload = {
            "configured": True,
            "adapter": getattr(settings, "LOYALTY_ADAPTER", "") or "unknown",
            "available": False,
            "message": (
                "Loyalty credentials are present but a live provider integration "
                "is not implemented. Balances are not available."
            ),
        }
    return payload
