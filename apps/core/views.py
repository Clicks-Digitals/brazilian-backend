from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import AuditLog
from apps.core.pagination import AdminPagination
from apps.core.permissions import HasPermissionCode, IsStaffUser
from rest_framework.permissions import IsAuthenticated


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({"status": "ok", "service": "brazilian-coffee-house"})


class AdminAuditLogView(APIView):
    permission_classes = [IsAuthenticated, IsStaffUser, HasPermissionCode]
    permission_code = "audit.view"

    def get(self, request):
        qs = AuditLog.objects.select_related("actor").all()
        entity_type = request.query_params.get("entity_type")
        action = request.query_params.get("action")
        if entity_type:
            qs = qs.filter(entity_type=entity_type)
        if action:
            qs = qs.filter(action=action)
        paginator = AdminPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        results = [
            {
                "id": log.id,
                "actor": log.actor.email if log.actor_id else None,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "metadata": log.metadata,
                "ip_address": log.ip_address,
                "created_at": log.created_at,
            }
            for log in page
        ]
        return paginator.get_paginated_response(results)
