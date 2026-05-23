from __future__ import annotations

import uuid
from pathlib import Path

from django.core.files.base import ContentFile

PROFILE_MEDIA_ROOT = "profile_pictures/users"


def profile_picture_upload_to(instance, filename: str) -> str:
    """WebP profile images live under ``profile_pictures/users/<id>/``."""
    name = Path(filename or "avatar.webp").name
    if not name.lower().endswith(".webp"):
        name = f"{Path(name).stem or 'avatar'}.webp"
    if getattr(instance, "pk", None):
        return f"{PROFILE_MEDIA_ROOT}/{instance.pk}/{name}"
    return f"{PROFILE_MEDIA_ROOT}/staging/{uuid.uuid4().hex}/{name}"


def profile_picture_needs_finalize(stored_name: str, user_id: int) -> bool:
    if not stored_name or not user_id:
        return False
    final_prefix = f"{PROFILE_MEDIA_ROOT}/{user_id}/"
    return not (
        stored_name.startswith(final_prefix) and stored_name.lower().endswith(".webp")
    )


def finalize_profile_picture(user) -> bool:
    if not user.profile_picture or not user.id:
        return False

    old_name = str(user.profile_picture.name)
    if not profile_picture_needs_finalize(old_name, user.id):
        return False

    file_name = Path(old_name).name
    if not file_name.lower().endswith(".webp"):
        file_name = f"{Path(file_name).stem or 'avatar'}.webp"
    new_name = f"{PROFILE_MEDIA_ROOT}/{user.id}/{file_name}"

    if old_name == new_name:
        return False

    raw = user.profile_picture.storage.open(old_name, "rb").read()
    user.profile_picture.save(new_name, ContentFile(raw), save=False)
    if old_name != new_name:
        try:
            user.profile_picture.storage.delete(old_name)
        except Exception:
            pass
    return True
