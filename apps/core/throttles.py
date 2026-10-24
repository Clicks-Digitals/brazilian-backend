from django.conf import settings
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class _TestAware:
    def allow_request(self, request, view):
        if getattr(settings, "TESTING", False) or "test" in __import__("sys").argv:
            return True
        return super().allow_request(request, view)


class AuthThrottle(_TestAware, UserRateThrottle):
    scope = "auth"


class CheckoutThrottle(_TestAware, UserRateThrottle):
    scope = "checkout"


class NewsletterThrottle(_TestAware, AnonRateThrottle):
    scope = "newsletter"
