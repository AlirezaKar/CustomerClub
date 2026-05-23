"""
Base view for server-to-server integration endpoints.

These routes authenticate via X-Management-API-Key, not user JWTs. DRF's default
anon/user throttles must not apply or the kiosk will exhaust 100 requests/hour.
"""
from rest_framework.views import APIView

from .integration_permissions import ManagementServiceAPIPermission


class IntegrationAPIView(APIView):
    authentication_classes = []
    permission_classes = [ManagementServiceAPIPermission]
    throttle_classes = []
