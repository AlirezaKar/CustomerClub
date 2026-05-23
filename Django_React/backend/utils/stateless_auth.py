"""
JWT authentication for the stateless kiosk (no local User rows).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken


@dataclass
class KioskEndUser:
    """In-memory end user referenced only by management primary key."""

    id: int
    phone_number: str
    score: int = 0
    first_name: str = ""
    last_name: str = ""
    username: str = ""
    is_authenticated: bool = True
    is_active: bool = True

    @property
    def pk(self) -> int:
        return self.id

    def __int__(self) -> int:
        return self.id


class KioskRefreshToken(RefreshToken):
    @classmethod
    def for_kiosk_user(cls, user_id: int) -> "KioskRefreshToken":
        token = cls()
        token["user_id"] = int(user_id)
        return token


def issue_tokens_for_user_id(user_id: int) -> dict[str, str]:
    refresh = KioskRefreshToken.for_kiosk_user(user_id)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


class KioskJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token: dict[str, Any]):
        user_id = validated_token.get("user_id")
        if not user_id:
            return AnonymousUser()
        return KioskEndUser(
            id=int(user_id),
            phone_number="",
            username=str(user_id),
        )
