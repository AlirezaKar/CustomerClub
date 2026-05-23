from rest_framework import serializers

from module_product import serializers as module_product_serializers
from django.utils import timezone
from datetime import timedelta
from . import models


class UserSerializer(serializers.ModelSerializer):
    # useroffer_set= module_product_serializers.UserOfferSerializer(read_only= True, many= True) # not ordering by offer_rate
    useroffer_set= serializers.SerializerMethodField() # ordering by offer_rate

    class Meta:
        model= models.User
        # fields= "__all__"
        fields= ["first_name", "last_name", "phone_number", "score", "useroffer_set"]

    def get_useroffer_set(self, instance):
        useroffer = instance.get_useroffer_set()
        shop_id = self.context.get("shop_id")
        if shop_id is not None:
            useroffer = useroffer.filter(product__shop_id=shop_id)
        return module_product_serializers.UserOfferSerializer(useroffer, many=True).data


def _normalize_uid(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _validate_uid_format(uid: str) -> None:
    """
    Validate NFC UID format (hex string) with common byte lengths.

    Common UID lengths used by readers:
    - 4 bytes  -> 8 hex chars
    - 7 bytes  -> 14 hex chars
    - 10 bytes -> 20 hex chars
    """
    if not uid:
        raise serializers.ValidationError({"error": "uid required", "field": "uid"})

    uid_clean = uid.strip()
    if uid_clean != uid:
        # avoid subtle duplicates and mismatches
        uid = uid_clean

    allowed_lengths = (8, 14, 20)
    if len(uid) not in allowed_lengths:
        raise serializers.ValidationError({
            "error": "invalid uid format",
            "field": "uid",
            "hint": "UID must be a hex string with length 8, 14, or 20.",
        })

    try:
        int(uid, 16)
    except ValueError as exc:
        raise serializers.ValidationError({
            "error": "invalid uid format",
            "field": "uid",
            "hint": "UID must be a hex string with length 8, 14, or 20.",
        }) from exc


class NfcRegisterSerializer(serializers.Serializer):
    """
    Register/link an NFC tag to a user.

    Input: raw `uid` (hex). Storage: hashed uid in `NFCTag.uid`.
    """

    uid = serializers.CharField(required=True, allow_blank=False, trim_whitespace=True)

    def validate_uid(self, value: str) -> str:
        uid = _normalize_uid(value)
        _validate_uid_format(uid)
        return uid.lower()

    def create(self, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            raise serializers.ValidationError({"error": "authentication required"})

        raw_uid: str = validated_data["uid"]
        hashed_uid = models.NFCTag.hash_uid(raw_uid)

        existing = models.NFCTag.objects.filter(uid=hashed_uid).first()
        if existing and existing.user_id != user.id:
            # UID already linked elsewhere
            raise serializers.ValidationError({"error": "uid already linked", "field": "uid"})
        if existing and existing.user_id == user.id and existing.is_active:
            raise serializers.ValidationError({"error": "uid already linked", "field": "uid"})

        tag, created = models.NFCTag.objects.get_or_create(
            uid=hashed_uid,
            defaults={"user": user, "is_active": True},
        )
        if not created:
            tag.user = user
            tag.is_active = True
            tag.save(update_fields=["user", "is_active"])
        return tag


class NfcLoginSerializer(serializers.Serializer):
    """
    Authenticate using an NFC UID.

    Security behavior:
    - Invalid UID returns a generic error (no account enumeration).
    - Locked tag returns a specific error to allow UI to show lock status.
    """

    uid = serializers.CharField(required=True, allow_blank=False, trim_whitespace=True)

    def validate_uid(self, value: str) -> str:
        uid = _normalize_uid(value)
        _validate_uid_format(uid)
        return uid.lower()

    def validate(self, attrs):
        raw_uid: str = attrs.get("uid") or ""
        hashed_uid = models.NFCTag.hash_uid(raw_uid)

        tag = models.NFCTag.objects.filter(uid=hashed_uid, is_active=True).select_related("user").first()
        if not tag:
            # Generic error for security (avoid telling whether UID exists)
            raise serializers.ValidationError({"error": "invalid credentials"})

        # Lock behavior: 5 consecutive failures -> 30 minutes lock.
        if tag.is_locked():
            raise serializers.ValidationError({"error": "nfc_tag_locked"})

        attrs["tag"] = tag
        return attrs

    def login(self) -> models.User:
        """
        Complete login and update tag metadata.
        Returns the authenticated user instance.
        """
        tag: models.NFCTag = self.validated_data["tag"]

        # Successful login => reset failures, update last_used_at.
        tag.reset_failed_attempts()
        tag.last_used_at = timezone.now()
        tag.save(update_fields=["last_used_at"])
        return tag.user

    def fail(self) -> None:
        """
        Record a failed login attempt for a tag (if resolvable).

        This should be called only when the caller has already matched a tag
        but some secondary check failed. For pure UID mismatch, we cannot
        safely increment without enumerating tags.
        """
        tag: models.NFCTag | None = self.validated_data.get("tag")
        if not tag:
            return

        # Ensure lock duration matches spec even if model defaults differ.
        max_attempts = 5
        lock_seconds = 30 * 60

        tag.failed_attempts = (tag.failed_attempts or 0) + 1
        if tag.failed_attempts >= max_attempts:
            tag.locked_until = timezone.now() + timedelta(seconds=lock_seconds)
        tag.save(update_fields=["failed_attempts", "locked_until"])


class NfcUnlinkSerializer(serializers.Serializer):
    """
    Unlink (deactivate) an NFC tag for the requesting user.
    Accepts either `uid` (raw hex) or `tag_id`.
    """

    uid = serializers.CharField(required=False, allow_blank=False, trim_whitespace=True)
    tag_id = serializers.IntegerField(required=False)

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            raise serializers.ValidationError({"error": "authentication required"})

        uid = _normalize_uid(attrs.get("uid"))
        tag_id = attrs.get("tag_id")
        if not uid and not tag_id:
            raise serializers.ValidationError({"error": "uid or tag_id required"})

        tag = None
        if tag_id:
            tag = models.NFCTag.objects.filter(id=tag_id, user=user).first()
        else:
            _validate_uid_format(uid)
            hashed_uid = models.NFCTag.hash_uid(uid.lower())
            tag = models.NFCTag.objects.filter(uid=hashed_uid, user=user).first()

        if not tag:
            raise serializers.ValidationError({"error": "nfc_tag_not_found"})

        attrs["tag"] = tag
        return attrs

    def save(self, **kwargs):
        tag: models.NFCTag = self.validated_data["tag"]
        tag.is_active = False
        tag.save(update_fields=["is_active"])
        return tag


class NfcTagSerializer(serializers.ModelSerializer):
    """
    Read serializer for NFC tags.

    Exposes only masked UID (never the stored hash as-is).
    """

    uid = serializers.SerializerMethodField()

    class Meta:
        model = models.NFCTag
        fields = ("id", "uid", "is_active", "created_at", "last_used_at", "failed_attempts", "locked_until")

    def get_uid(self, obj: models.NFCTag) -> str:
        return obj.mask_uid()


class NfcStatusSerializer(serializers.Serializer):
    """
    Report NFC status for a user: whether they have active tags and basic tag info.
    """

    has_active_nfc_tags = serializers.BooleanField()
    tags = serializers.ListField(child=serializers.DictField(), required=True)

    @staticmethod
    def from_user(user: models.User):
        qs = user.nfc_tags.all().order_by("-created_at")
        tags = NfcTagSerializer(qs, many=True).data
        return {
            "has_active_nfc_tags": qs.filter(is_active=True).exists(),
            "tags": tags,
        }
