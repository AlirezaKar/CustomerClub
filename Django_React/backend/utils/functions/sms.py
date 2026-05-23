from __future__ import annotations

import logging
from django.conf import settings

from ..utils import to_local_09

logger = logging.getLogger(__name__)


class SMSService:
    """Service for sending SMS via SMS.ir."""

    @staticmethod
    def send_verification_code(phone_e164: str, code: str) -> bool:
        """Send verification code via SMS.ir using OTP template.

        Args:
            phone_e164: Phone number in E.164 format (+98XXXXXXXXXX)
            code: Verification code to send

        Returns:
            True if SMS was sent successfully, False otherwise
        """
        api_key = getattr(settings, "SMSIR_API_KEY", "") or ""
        line_number = getattr(settings, "SMSIR_LINE_NUMBER", "") or ""
        template_id = getattr(settings, "SMSIR_TEMPLATE_ID", "") or ""

        if not api_key:
            logger.warning(
                "SMS config missing (SMSIR_API_KEY); "
                "skipping SMS send for phone: %s",
                phone_e164,
            )
            return False

        if not line_number:
            logger.warning(
                "SMS config missing (SMSIR_LINE_NUMBER); "
                "skipping SMS send for phone: %s",
                phone_e164,
            )
            return False

        if not template_id:
            logger.warning(
                "SMS template ID missing (SMSIR_TEMPLATE_ID); "
                "skipping SMS send for phone: %s",
                phone_e164,
            )
            return False

        try:
            local_09 = to_local_09(phone_e164)

            try:
                template_id_int = int(template_id)
            except (ValueError, TypeError):
                logger.error(
                    "Invalid template_id format: %s (must be numeric)", template_id
                )
                return False

            logger.info(
                "Attempting to send OTP SMS via sms.ir: phone=%s, template_id=%s (as int: %s)",
                local_09,
                template_id,
                template_id_int,
            )

            from sms_ir import SmsIr  # type: ignore

            client = SmsIr(api_key, line_number)

            parameters = [{"name": "VERIFY", "value": code}]
            logger.info(
                "Calling send_verify_code: phone=%s, template_id=%s, parameters=%s",
                local_09,
                template_id_int,
                parameters,
            )

            response = client.send_verify_code(local_09, template_id_int, parameters)

            logger.info(
                "SMS.ir send_verify_code response: phone=%s, response=%s, response_type=%s",
                local_09,
                response,
                type(response).__name__,
            )

            if hasattr(response, "status_code"):
                status_code = response.status_code
                logger.info("SMS.ir response status_code: %s", status_code)

                try:
                    if hasattr(response, "json"):
                        response_data = response.json()
                        logger.info("SMS.ir response JSON: %s", response_data)
                    elif hasattr(response, "_content"):
                        import json

                        response_data = json.loads(response._content.decode("utf-8"))
                        logger.info("SMS.ir response parsed: %s", response_data)
                    else:
                        response_data = None
                except Exception as parse_exc:
                    logger.warning("Failed to parse SMS.ir response: %s", parse_exc)
                    response_data = None

                if status_code >= 400:
                    error_message = "Unknown error"
                    if response_data:
                        error_message = response_data.get(
                            "message", str(response_data)
                        )
                    logger.error(
                        "SMS.ir API returned error: status_code=%s, message=%s, response=%s",
                        status_code,
                        error_message,
                        response_data,
                    )
                    return False

                if response_data:
                    logger.info("SMS.ir API success response: %s", response_data)
                logger.info("OTP SMS sent successfully via sms.ir: phone=%s", local_09)
                return True

            logger.info("SMS.ir response (non-Response): %s", response)
            logger.info("OTP SMS sent successfully via sms.ir: phone=%s", local_09)
            return True
        except Exception as exc:  # pragma: no cover
            logger.exception(
                "Failed to send SMS via sms.ir: phone=%s, template_id=%s, error=%s",
                phone_e164,
                template_id,
                exc,
            )
            return False