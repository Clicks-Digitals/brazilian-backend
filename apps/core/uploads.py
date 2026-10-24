from pathlib import Path

from django.conf import settings
from rest_framework.exceptions import ValidationError


def validate_image_file(uploaded) -> None:
    name = getattr(uploaded, "name", "") or ""
    suffix = Path(name).suffix.lower()
    if suffix not in settings.ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError("Unsupported image format. Use JPG, PNG, WEBP, or GIF.")
    size = getattr(uploaded, "size", 0) or 0
    if size > settings.MAX_IMAGE_SIZE_BYTES:
        raise ValidationError("Image is too large. Maximum size is 8 MB.")
    content_type = getattr(uploaded, "content_type", "") or ""
    if content_type and content_type not in settings.ALLOWED_IMAGE_MIME_TYPES:
        raise ValidationError("File MIME type is not an allowed image type.")
    header = uploaded.read(16)
    uploaded.seek(0)
    signatures = (
        b"\xff\xd8\xff",
        b"\x89PNG\r\n\x1a\n",
        b"RIFF",
        b"GIF87a",
        b"GIF89a",
    )
    if not any(header.startswith(sig) for sig in signatures):
        raise ValidationError("File content is not a valid image.")
