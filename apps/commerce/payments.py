from django.conf import settings

from apps.commerce.models import PaymentRecord


class PaymentError(Exception):
    pass


class NotConfigured(PaymentError):
    pass


class PaymentProvider:
    provider_name = "base"

    def create_payment(self, order, **kwargs) -> PaymentRecord:
        raise NotImplementedError


class CODProvider(PaymentProvider):
    provider_name = "cod"

    def create_payment(self, order, **kwargs) -> PaymentRecord:
        return PaymentRecord.objects.create(
            order=order,
            provider="cod",
            status=PaymentRecord.Status.PENDING,
            amount=order.total,
            currency=order.currency,
            raw_payload={"method": "cod"},
        )


class OnlinePaymentProvider(PaymentProvider):
    provider_name = "online"

    def __init__(self):
        if not getattr(settings, "PAYMENTS_PROVIDER", ""):
            raise NotConfigured("Online payments are not configured.")

    def create_payment(self, order, **kwargs) -> PaymentRecord:
        raise NotConfigured(
            f"Provider '{settings.PAYMENTS_PROVIDER}' is selected but no live gateway "
            "integration is implemented. Cash on delivery remains the available method."
        )


def get_payment_provider(method: str) -> PaymentProvider:
    if method == "cod":
        return CODProvider()
    return OnlinePaymentProvider()
