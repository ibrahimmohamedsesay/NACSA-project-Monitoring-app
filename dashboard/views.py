import datetime
import json
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum, Q
from django.shortcuts import render

from audit.models import AuditLog
from beneficiaries.models import Beneficiary, BeneficiaryProject
from core.permissions import can, is_admin
from finance.models import Payment
from grm.models import GRMCase
from monitoring.models import ProgressUpdate
from projects.models import Project
from documents.models import Document


@login_required
def index(request):
    u = request.user
    today = datetime.date.today()
    projects = Project.objects.filter(is_archived=False)
    ctx = {"page_title": "Dashboard"}
    st = {s: 0 for s, _ in Project.STATUS_CHOICES}
    for row in projects.values("status").annotate(n=Count("id")):
        st[row["status"]] = row["n"]
    active = st["ongoing"] + st["at_risk"] + st["delayed"] + st["planned"]
    ctx["stats"] = {
        "total": projects.count(),
        "ongoing": st["ongoing"],
        "completed": st["completed"],
        "delayed": st["delayed"] + projects.filter(status__in=["ongoing", "planned"], expected_completion_date__lt=today).count(),
        "at_risk": st["at_risk"],
        "pending_approval": st["submitted"] + st["under_review"],
        "budget": projects.aggregate(s=Sum("budget"))["s"] or Decimal("0"),
        "active": active,
    }
    ctx["avg_progress"] = round(sum(p.completion_percentage for p in projects.filter(status__in=["ongoing", "at_risk", "delayed"])) / max(projects.filter(status__in=["ongoing", "at_risk", "delayed"]).count(), 1))
    if can(u, "beneficiaries", "view"):
        ctx["beneficiaries"] = Beneficiary.objects.count()
        ctx["serviced"] = BeneficiaryProject.objects.filter(status="serviced").count()
    if can(u, "finance", "view"):
        paid = Payment.objects.filter(status="paid").aggregate(s=Sum("amount"))["s"] or Decimal("0")
        pending = Payment.objects.exclude(status="paid").aggregate(s=Sum("amount"))["s"] or Decimal("0")
        ctx["paid"], ctx["pending_pay"] = paid, pending
    if can(u, "grm", "view"):
        ctx["open_grm"] = GRMCase.objects.filter(status__in=["open", "under_review"]).count()
    if can(u, "monitoring", "review"):
        ctx["pending_reviews"] = ProgressUpdate.objects.filter(review_status="pending_review").count()
    # charts
    status_data = [(label, st[key]) for key, label in Project.STATUS_CHOICES if st[key]]
    district = list(projects.values("district").annotate(n=Count("id")).order_by("-n")[:10])
    types = list(projects.exclude(project_type="").values("project_type").annotate(n=Count("id")).order_by("-n"))
    ctx["chart_data"] = ({
        "status": {"labels": [a for a, _ in status_data], "values": [b for _, b in status_data]},
        "district": {"labels": [d["district"] for d in district], "values": [d["n"] for d in district]},
        "types": {"labels": [t["project_type"] for t in types], "values": [t["n"] for t in types]},
    })
    # attention lists
    ctx["delayed_projects"] = [p for p in projects.filter(status__in=["ongoing", "at_risk", "delayed", "planned"]).select_related("officer") if p.health in ("Delayed", "At risk")][:6]
    ctx["awaiting"] = projects.filter(status__in=["submitted", "under_review"]).order_by("-updated_at")[:5] if can(u, "projects", "approve") or is_admin(u) else []
    ctx["recent_projects"] = projects.order_by("-updated_at")[:6]
    ctx["recent_updates"] = ProgressUpdate.objects.select_related("project", "officer").order_by("-created_at")[:5] if can(u, "monitoring", "view") else []
    if is_admin(u) or u.role_name == "management":
        ctx["activity"] = AuditLog.objects.select_related("user").order_by("-timestamp")[:8]
    ctx["is_empty"] = not projects.exists()
    return render(request, "dashboard/index.html", ctx)


@login_required
def search(request):
    q = request.GET.get("q", "").strip()
    res = {}
    if q:
        u = request.user
        res["projects"] = Project.objects.filter(Q(name__icontains=q) | Q(project_id__icontains=q) | Q(community__icontains=q) | Q(district__icontains=q))[:10]
        if can(u, "beneficiaries", "view"):
            res["beneficiaries"] = Beneficiary.objects.filter(Q(name__icontains=q) | Q(community__icontains=q))[:10]
        if can(u, "documents", "view"):
            res["documents"] = Document.objects.filter(Q(project__name__icontains=q) | Q(category__icontains=q)).select_related("project")[:10]
        if can(u, "grm", "view"):
            res["cases"] = GRMCase.objects.filter(Q(case_id__icontains=q) | Q(complainant__icontains=q) | Q(category__icontains=q))[:10]
    return render(request, "dashboard/search.html", {"q": q, "res": res, "page_title": "Search"})
