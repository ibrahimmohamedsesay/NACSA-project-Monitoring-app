from audit.models import AuditLog


def log(user, action, module, record_id="", description=""):
    """Write one audit trail entry. Never raises into the calling view."""
    try:
        AuditLog.objects.create(
            user=user if getattr(user, "is_authenticated", False) else None,
            action=action[:255],
            module=module[:50],
            record_id=str(record_id)[:50],
            description=description[:500],
        )
    except Exception:  # pragma: no cover - audit must never break a request
        pass
