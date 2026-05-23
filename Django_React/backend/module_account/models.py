from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db import models
from django.core.cache import cache
from django.utils import timezone
from datetime import datetime, timedelta
import json
import time as _time
from pathlib import Path as _Path
import hashlib

# utils
from utils.functions import user as user_functions
from utils.functions import datetime
from utils.functions import sms as sms_functions


# region agent log
def _agent_log(hypothesis_id, location, message, data):
    try:
        log_path = _Path(__file__).resolve().parents[2] / "debug-2b8592.log"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "sessionId": "2b8592",
                "runId": "initial",
                "hypothesisId": hypothesis_id,
                "location": location,
                "message": message,
                "data": data,
                "timestamp": int(_time.time() * 1000),
            }) + "\n")
    except Exception:
        # ignore logging errors
        pass
# endregion

GENDERS= (
    ("male", "Male"),
    ("female", "Female"),
)

class User(AbstractUser):
    phone_number= models.CharField(max_length=11, unique=True, blank=True, null=True)
    age= models.PositiveIntegerField(blank= True, null= True)
    gender= models.CharField(max_length= 10, choices= GENDERS, blank= True, null= True)
    score= models.PositiveIntegerField(default= 0)
    card_uid= models.CharField(max_length= 255, blank= True, null= True)
    # NOTE: keep this field nullable so we can clear it after successful login.
    # We intentionally avoid storing a long-lived reusable code.
    phone_number_verification_code= models.PositiveBigIntegerField(blank=True, null=True)
    phone_number_verification_code_last_change= models.DateTimeField(blank= True, null=True)
    phone_number_verification_code_last_send= models.DateTimeField(blank= True, null= True)

    def __str__(self):
        return f"{self.username if self.username else 'None'} | {self.phone_number if self.phone_number else 'None'}"

    def save(self, *args, **kwargs):
        # Do NOT generate a verification code on user creation/save.
        # Codes are generated only when sending a login SMS.
        super().save(*args, **kwargs)

    def update_verification_code(self, successful_use= False):
        if successful_use:
            # Clear the code after successful use so it can't be reused/leaked.
            self.phone_number_verification_code= None
            self.phone_number_verification_code_last_change= datetime.now()
            self.save(update_fields=["phone_number_verification_code", "phone_number_verification_code_last_change"])
            return

        # If code is missing OR expired => generate a new one
        if self.phone_number_verification_code is None:
            self.phone_number_verification_code= user_functions.generate_phone_number_verification_code()
            self.phone_number_verification_code_last_change= datetime.now()
            self.save(update_fields=["phone_number_verification_code", "phone_number_verification_code_last_change"])
            return

        if self.phone_number_verification_code_last_change and ((datetime.now()- self.phone_number_verification_code_last_change).seconds >= settings.PHONE_NUMBER_VERIFICATION_CODE_LIFE):
            self.phone_number_verification_code= user_functions.generate_phone_number_verification_code()
            self.phone_number_verification_code_last_change= datetime.now()
            self.save(update_fields=["phone_number_verification_code", "phone_number_verification_code_last_change"])

    def send_verification_code(self):
        # Per-session resend limit (keyed by phone_number in cache).
        max_resends = int(getattr(settings, "SMS_MAX_RESENDS_PER_SESSION", 5))
        session_ttl = int(getattr(settings, "SMS_RESEND_SESSION_TTL", getattr(settings, "PHONE_NUMBER_VERIFICATION_CODE_LIFE", 300)))
        cache_key = f"sms_resend:{self.phone_number}"
        try:
            current_resends = int(cache.get(cache_key) or 0)
        except Exception:
            current_resends = 0

        if current_resends >= max_resends:
            return False, "resend_limit_reached"

        try:
            if self.phone_number_verification_code_last_send:
                delta_seconds = (datetime.now() - self.phone_number_verification_code_last_send).seconds
            else:
                delta_seconds = None
        except Exception:
            delta_seconds = None
    
        # Check rate limit (skip in debug mode)
        if not getattr(settings, "SMS_DEBUG_MODE", False):
            if self.phone_number_verification_code_last_send:
                elapsed = (datetime.now() - self.phone_number_verification_code_last_send).seconds
                if elapsed < settings.PHONE_NUMBER_VERIFICATION_CODE_SEND_LIMIT:
                    remaining = settings.PHONE_NUMBER_VERIFICATION_CODE_SEND_LIMIT - elapsed
                    return False, remaining

        # Consume one resend attempt for this session window.
        try:
            cache.set(cache_key, current_resends + 1, timeout=session_ttl)
        except Exception:
            pass
    
        # Update verification code before sending
        self.update_verification_code()
        
        # Get the verification code
        code = self.phone_number_verification_code
        if code is None:
            return False, "code_generation_failed"
        code_str = str(code).zfill(settings.PHONE_NUMBER_VERIFICATION_CODE_LENGTH)
        
        # Debug mode - just print the code
        if getattr(settings, "SMS_DEBUG_MODE", False):
            print(f"\n" + "="*50)
            print(f"📱 DEBUG MODE ACTIVATED")
            print(f"Phone: {self.phone_number}")
            print(f"Verification Code: {code_str}")
            print(f"="*50 + "\n")
            
            # Update last send time
            self.phone_number_verification_code_last_send = datetime.now()
            self.save(update_fields=["phone_number_verification_code_last_send"])
            return True, None
        
        # Regular SMS sending (when debug mode is off)
        try:
            from utils.functions.sms import SMSService

            ok = SMSService.send_verification_code(self.phone_number, code_str)
            if not ok:
                return False, "sms_failed"

            self.phone_number_verification_code_last_send = datetime.now()
            self.save(update_fields=["phone_number_verification_code_last_send"])
            return True, None
        except Exception as exc:
            _agent_log(
                "H1",
                "backend/module_account/models.py:send_verification_code",
                "send_verification_code_sms_failed",
                {
                    "userId": self.id,
                    "error": str(exc),
                },
            )
            return False, "sms_failed"

    def get_useroffer_set(self):
        # Only show offers the user is currently eligible to take.
        # (Prevents showing items with required score above user's score.)
        return (
            self.useroffer_set.filter(
                product__is_active=True,
                product__is_offerable=True,
                product__score__lte=self.score,
            )
            .order_by("-offer_rate")
        )


class NFCTag(models.Model):
    """
    NFC tag assigned to a user for NFC-based authentication.

    Notes:
    - `uid` is stored as a hashed identifier (e.g. SHA256 hex digest), not the raw UID.
    - Lockout is tag-scoped: repeated failures can temporarily lock this tag.
    """

    uid = models.CharField(max_length=128, unique=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="nfc_tags",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    failed_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.mask_uid()} → {getattr(self.user, 'phone_number', self.user_id)}"

    @staticmethod
    def hash_uid(raw_uid: str) -> str:
        """
        Hash a raw UID before storage.
        Uses SHA256 hex digest (length=64) which fits in `uid` (max_length=128).
        """
        normalized = (raw_uid or "").strip()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def mask_uid(self) -> str:
        """
        Returns a masked identifier for display/logging.

        Since we store hashed UIDs, this returns the last 4 chars of the stored `uid`.
        """
        if not self.uid:
            return "****"
        tail = self.uid[-4:] if len(self.uid) >= 4 else self.uid
        return f"****{tail}"

    def is_locked(self) -> bool:
        """True if this tag is currently locked due to failed attempts."""
        return bool(self.locked_until and self.locked_until > timezone.now())

    def increment_failed_attempts(self) -> None:
        """
        Increment failed attempts and apply lockout if threshold reached.

        Non-obvious logic:
        - Threshold and lock duration are configurable via settings:
          - `NFC_TAG_MAX_FAILED_ATTEMPTS` (default 5)
          - `NFC_TAG_LOCK_SECONDS` (default 300)
        """
        self.failed_attempts = (self.failed_attempts or 0) + 1
        max_attempts = int(getattr(settings, "NFC_TAG_MAX_FAILED_ATTEMPTS", 5))
        lock_seconds = int(getattr(settings, "NFC_TAG_LOCK_SECONDS", 300))

        if self.failed_attempts >= max_attempts:
            self.locked_until = timezone.now() + timedelta(seconds=lock_seconds)
        self.save(update_fields=["failed_attempts", "locked_until"])

    def reset_failed_attempts(self) -> None:
        """Reset the failure counter and clear lockout (call on successful login)."""
        self.failed_attempts = 0
        self.locked_until = None
        self.save(update_fields=["failed_attempts", "locked_until"])
