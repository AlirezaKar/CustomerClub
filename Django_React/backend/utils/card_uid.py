"""
Normalize raw NFC scanner UIDs and stable uid_code values for management lookups.
"""
from __future__ import annotations

from module_account.models import NFCTag

_RAW_UID_LENGTHS = (8, 14, 20)


def _looks_like_raw_nfc_uid(value: str) -> bool:
    if len(value) not in _RAW_UID_LENGTHS:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def normalize_card_identifier(value: str) -> str:
    """
    Return the stable uid_code stored for a card.

    Raw scanner UIDs (8/14/20 hex) are hashed once; values that are already
    hashed (or other stored identifiers) are returned lowercased as-is.
    """
    normalized = (value or "").strip().lower()
    if not normalized:
        return ""
    if _looks_like_raw_nfc_uid(normalized):
        return NFCTag.hash_uid(normalized)
    return normalized


def card_lookup_candidates(value: str) -> list[str]:
    """Identifiers to try when resolving a card (supports legacy raw storage)."""
    normalized = (value or "").strip().lower()
    if not normalized:
        return []
    stable = normalize_card_identifier(normalized)
    if stable == normalized:
        return [stable]
    return [stable, normalized]
