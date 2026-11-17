from django.conf import settings
from django.urls import reverse

from core.permissions import can, role_of, is_admin

NAV = [
    ("Dashboard", "bi-speedometer2", "dashboard:index", "dashboard", "dashboard"),
    ("Projects", "bi-folder2-open", "projects:list", "projects", "projects"),
    ("Monitoring & M&E", "bi-clipboard-data", "monitoring:dashboard", "monitoring", "monitoring"),
    ("Results Framework", "bi-bullseye", "results:list", "results", "results"),
    ("Beneficiaries", "bi-people", "beneficiaries:dashboard", "beneficiaries", "beneficiaries"),
    ("Finance & Payments", "bi-cash-coin", "finance:dashboard", "finance", "finance"),
    ("GRM", "bi-chat-left-text", "grm:dashboard", "grm", "grm"),
    ("Documents", "bi-file-earmark-text", "documents:list", "documents", "documents"),
    ("Reports & Analytics", "bi-bar-chart-line", "reports:index", "reports", "reports"),
    ("Notifications", "bi-bell", "notifications:list", "notifications", "notifications"),
    ("Users", "bi-person-gear", "accounts:user_list", "users", "accounts_admin"),
    ("Audit Trail", "bi-shield-check", "audit:list", "audit", "audit"),
    ("Settings", "bi-gear", "accounts:profile", "profile", "accounts"),
]


def nacsa(request):
    ctx = {"SYSTEM_NAME": settings.SYSTEM_NAME}
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return ctx
    match = request.resolver_match
    ns = match.namespace if match else ""
    items = []
    for label, icon, url, module, ns_key in NAV:
        if module == "users" and not is_admin(user):
            continue
        if module == "audit" and not is_admin(user):
            continue
        if module not in ("profile", "users", "audit") and not can(user, module, "view"):
            continue
        active = ns == ns_key or (ns_key == "accounts" and ns == "accounts" and match.url_name == "profile")
        if ns_key == "accounts_admin":
            active = ns == "accounts" and match.url_name.startswith("user")
        if ns_key == "accounts":
            active = ns == "accounts" and not match.url_name.startswith("user")
        items.append({"label": label, "icon": icon, "url": reverse(url), "active": active})
    from notifications.models import Notification
    ctx.update(
        nav_items=items,
        unread_count=Notification.objects.filter(user=user, is_read=False).count(),
        user_role_label=user.role.get_name_display() if user.role else ("Administrator" if user.is_superuser else "No role"),
        current_role=role_of(user),
    )
    return ctx
