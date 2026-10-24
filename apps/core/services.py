from apps.core.models import AuditLog
from apps.core.utils import client_ip


def write_audit(request, action: str, entity_type: str, entity_id="", metadata=None):
    actor = None
    ip_address = None
    if request is not None:
        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            actor = user
        ip_address = client_ip(request)
    return AuditLog.objects.create(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else "",
        metadata=metadata or {},
        ip_address=ip_address,
    )
