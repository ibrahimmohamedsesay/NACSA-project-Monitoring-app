from django.db.models import Q
from django.shortcuts import render

from core.permissions import admin_required
from core.utils import paginate
from .models import AuditLog


@admin_required
def audit_list(request):
    g = request.GET
    qs = AuditLog.objects.select_related("user")
    if g.get("q"):
        qs = qs.filter(Q(description__icontains=g["q"]) | Q(record_id__icontains=g["q"]) | Q(action__icontains=g["q"]))
    if g.get("module"):
        qs = qs.filter(module=g["module"])
    if g.get("user"):
        qs = qs.filter(user_id=g["user"])
    if g.get("from"):
        qs = qs.filter(timestamp__date__gte=g["from"])
    if g.get("to"):
        qs = qs.filter(timestamp__date__lte=g["to"])
    from django.contrib.auth import get_user_model
    page, params = paginate(request, qs, 25)
    return render(request, "audit/list.html", {
        "page": page, "params": params, "g": g, "page_title": "Audit trail",
        "modules": AuditLog.objects.values_list("module", flat=True).distinct().order_by("module"),
        "users": get_user_model().objects.filter(audit_logs__isnull=False).distinct()})
