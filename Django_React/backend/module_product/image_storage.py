from __future__ import annotations

import uuid
from pathlib import Path

from django.core.files.base import ContentFile

from utils.functions import images as image_functions

PRODUCT_MEDIA_ROOT = "module_product/products"


def product_image_upload_to(instance, filename: str) -> str:
    """Stage new uploads until the product row has a primary key."""
    safe_name = Path(filename or "image").name
    if getattr(instance, "pk", None):
        return f"{PRODUCT_MEDIA_ROOT}/{instance.pk}/{safe_name}"
    return f"{PRODUCT_MEDIA_ROOT}/staging/{uuid.uuid4().hex}/{safe_name}"


def product_image_needs_finalize(stored_name: str, product_id: int) -> bool:
    if not stored_name or not product_id:
        return False
    final_prefix = f"{PRODUCT_MEDIA_ROOT}/{product_id}/"
    return not (
        stored_name.startswith(final_prefix) and stored_name.lower().endswith(".webp")
    )


def finalize_product_image(product) -> bool:
    """
    Move/convert the stored file to ``module_product/products/<id>/<name>.webp``.
    Returns True when the database field was updated.
    """
    if not product.image or not product.id:
        return False

    old_name = str(product.image.name)
    if not product_image_needs_finalize(old_name, product.id):
        return False

    file_name = Path(old_name).name
    new_file_name = (
        file_name if file_name.lower().endswith(".webp") else image_functions.webp_name_for(file_name)
    )
    new_name = f"{PRODUCT_MEDIA_ROOT}/{product.id}/{new_file_name}"

    raw = product.image.storage.open(old_name, "rb").read()
    needs_convert = not old_name.lower().endswith(".webp")
    out_bytes = raw if not needs_convert else image_functions.convert_image_bytes_to_webp(raw)

    if old_name == new_name and not needs_convert:
        return False

    product.image.save(new_name, ContentFile(out_bytes), save=False)
    if old_name != new_name:
        try:
            product.image.storage.delete(old_name)
        except Exception:
            pass
    return True
