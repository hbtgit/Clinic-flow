from .models import AuditEvent


def record(request, action: str, target=None, **detail) -> AuditEvent:
    """Write an audit event for the current user. Never put patient details in `detail`."""
    user = request.user if request.user.is_authenticated else None
    return AuditEvent.objects.create(
        clinic=getattr(user, "clinic", None) or getattr(target, "clinic", None),
        actor=user,
        action=action,
        target_type=target._meta.label if target is not None else "",
        target_id=str(target.pk) if target is not None else "",
        detail=detail,
    )
