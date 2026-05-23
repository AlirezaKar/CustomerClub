from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps


def convert_image_bytes_to_webp(
    raw_bytes: bytes,
    *,
    quality: int = 82,
    method: int = 6,
) -> bytes:
    """Convert arbitrary image bytes to WebP bytes."""
    if not raw_bytes:
        raise ValueError("raw_bytes is empty")

    with Image.open(BytesIO(raw_bytes)) as img:
        img = ImageOps.exif_transpose(img)

        has_alpha = ("A" in img.getbands()) or (img.mode in ("LA", "RGBA"))
        if has_alpha:
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")

        out = BytesIO()
        img.save(out, format="WEBP", quality=quality, method=method)
        return out.getvalue()


def webp_name_for(original_name: str) -> str:
    """Return file name (not path) with ``.webp`` extension."""
    p = Path(original_name or "image")
    stem = p.stem or "image"
    return f"{stem}.webp"
