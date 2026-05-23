import secrets

from django.conf import settings
from rest_framework.permissions import BasePermission


class ManagementServiceAPIPermission(BasePermission):
    """Allow server-to-server calls from the main CustomerClub API using a shared key."""

    message = "Invalid or missing service API key."

    def has_permission(self, request, view):
        expected = getattr(settings, "MANAGEMENT_SERVICE_API_KEY", "") or ""
        if not expected:
            return False
        provided = (
            request.headers.get("X-Management-API-Key")
            or request.headers.get("X-Service-API-Key")
            or ""
        )
        if not provided and request.query_params.get("api_key"):
            provided = request.query_params.get("api_key")
        return secrets.compare_digest(str(provided), str(expected))
