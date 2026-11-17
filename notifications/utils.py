from notifications.models import Notification


def notify(users, event_type, message, link=""):
    """Create one in-system notification per user (skips duplicates/None)."""
    seen = set()
    for u in users:
        if u is None or u.pk in seen or not u.is_active:
            continue
        seen.add(u.pk)
        Notification.objects.create(user=u, event_type=event_type, message=message[:255], link=link)


def users_with_roles(*role_names):
    from django.contrib.auth import get_user_model
    from django.db.models import Q
    return get_user_model().objects.filter(
        Q(role__name__in=role_names) | Q(is_superuser=True), is_active=True
    ).distinct()
