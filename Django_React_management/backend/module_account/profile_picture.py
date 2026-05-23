"""Profile picture validation, WebP conversion, and size limits."""

from __future__ import annotations

import uuid
from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

# Incoming upload cap (larger files are compressed down when possible).
PROFILE_PICTURE_MAX_UPLOAD_BYTES = 2 * 1024 * 1024
# Stored profile pictures are always WebP and must not exceed this size.
PROFILE_PICTURE_MAX_BYTES = 500 * 1024

ALLOWED_IMAGE_CONTENT_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
    }
)


class ProfilePictureError(ValueError):
    """Raised when a profile picture cannot be accepted or processed."""


def process_profile_picture(uploaded_file) -> ContentFile:
    """
    Read an uploaded image, convert to WebP, and return a ``ContentFile`` <= 500KB.
    """
    uploaded_file.seek(0)
    raw = uploaded_file.read()
    if not raw:
        raise ProfilePictureError("Empty image file.")

    if len(raw) > PROFILE_PICTURE_MAX_UPLOAD_BYTES:
        raise ProfilePictureError(
            f"Image is too large. Maximum upload size is {PROFILE_PICTURE_MAX_UPLOAD_BYTES // 1024}KB."
        )

    content_type = getattr(uploaded_file, "content_type", None) or ""
    if content_type and content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise ProfilePictureError("Unsupported image type. Use JPG, PNG, WebP, or GIF.")

    try:
        image = Image.open(BytesIO(raw))
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise ProfilePictureError("Invalid or corrupted image file.") from exc

    image = ImageOps.exif_transpose(image)
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA" if "A" in image.getbands() else "RGB")

    max_dim = 1024
    if max(image.size) > max_dim:
        image.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

    quality = 85
    while quality >= 40:
        buffer = BytesIO()
        image.save(buffer, format="WEBP", quality=quality, method=6)
        webp_bytes = buffer.getvalue()
        if len(webp_bytes) <= PROFILE_PICTURE_MAX_BYTES:
            return ContentFile(webp_bytes, name=f"{uuid.uuid4().hex}.webp")
        quality -= 10

    raise ProfilePictureError(
        "Image could not be reduced below 500KB. Please use a smaller or simpler photo."
    )
