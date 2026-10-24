from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import urljoin

from django.conf import settings

MONEY_QUANT = Decimal("0.001")


def money(value) -> Decimal:
    if value is None:
        return Decimal("0.000")
    return Decimal(str(value)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def absolute_uri(request, file_or_url) -> str | None:
    if not file_or_url:
        return None
    url = file_or_url.url if hasattr(file_or_url, "url") else str(file_or_url)
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if request is not None:
        return request.build_absolute_uri(url)
    base = getattr(settings, "FRONTEND_URL", "")
    media_host = str(getattr(settings, "MEDIA_URL", "/media/"))
    if url.startswith("/"):
        return urljoin("http://localhost:8000", url)
    return urljoin(media_host, url)


def parse_bool(value, default=None):
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
