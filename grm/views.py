from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from audit.utils import log
from core.permissions import can, module_required
from core.utils import paginate
from notifications.utils import notify, users_with_roles
from projects.models import Project
from .forms import ActivityForm, CaseForm
from .models import GRMCase


@module_required("grm", "view")
def dashboard(request):
    qs = GRMCase.objects.all()
    st = {r["status"]: r["n"] for r in qs.values("status").annotate(n=Count("id"))}
    return render(request, "grm/dashboard.html", {
        "page_title": "Grievance redress", "st": st, "total": qs.count(),
        "by_category": qs.exclude(category="").values("category").annotate(n=Count("id")).order_by("-n"),
        "recent": qs.select_related("project", "assigned_to")[:8],
        "open_old": qs.filter(status__in=["open", "under_review"]).order_by("created_at")[:5]})


@module_required("grm", "view")
def case_list(request):
    g = request.GET
    qs = GRMCase.objects.select_related("project", "assigned_to")
    if g.get("status"):
        qs = qs.filter(status=g["status"])
    if g.get("project"):
        qs = qs.filter(project_id=g["project"])
    if g.get("category"):
        qs = qs.filter(category=g["category"])
    if g.get("q"):
        qs = qs.filter(Q(case_id__icontains=g["q"]) | Q(complainant__icontains=g["q"]) | Q(description__icontains=g["q"]))
    page, params = paginate(request, qs)
    from .forms import CATEGORIES
    return render(request, "grm/list.html", {"page": page, "params": params, "g": g, "page_title": "GRM cases", "statuses": GRMCase.STATUS_CHOICES,
                                             "categories": CATEGORIES, "projects": Project.objects.filter(grm_cases__isnull=False).distinct()})


@module_required("grm", "add")
def case_create(request):
    form = CaseForm(request.POST or None, initial={"project": request.GET.get("project")})
    if request.method == "POST" and form.is_valid():
        c = form.save()
        log(request.user, "create", "grm", c.pk, f"Opened grievance {c.case_id} ({c.category})")
        notify(users_with_roles("project_manager", "me_officer") if c.project else [], "grm_case_updated", f"New grievance {c.case_id}: {c.category}", reverse("grm:detail", args=[c.pk]))
        notify([c.assigned_to], "grm_case_updated", f"Grievance {c.case_id} was assigned to you.", reverse("grm:detail", args=[c.pk]))
        messages.success(request, f"Case {c.case_id} created.")
        return redirect("grm:detail", pk=c.pk)
    return render(request, "generic_form.html", {"form": form, "page_title": "Register grievance", "cancel_url": "/grm/cases/"})


@module_required("grm", "view")
def case_detail(request, pk):
    c = get_object_or_404(GRMCase.objects.select_related("project", "assigned_to"), pk=pk)
    form = ActivityForm(request.POST or None)
    if request.method == "POST":
        if not can(request.user, "grm", "edit"):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        if form.is_valid():
            a = form.save(commit=False)
            a.case, a.created_by = c, request.user
            a.save()
            ns = form.cleaned_data.get("new_status")
            if ns and ns != c.status:
                c.status = ns
                c.save(update_fields=["status", "updated_at"])
            log(request.user, "update", "grm", c.pk, f"{c.case_id}: {a.action} (status {c.status})")
            notify([c.assigned_to], "grm_case_updated", f"{c.case_id} updated: {a.action}", reverse("grm:detail", args=[c.pk]))
            messages.success(request, "Case updated.")
            return redirect("grm:detail", pk=c.pk)
    return render(request, "grm/detail.html", {"c": c, "form": form, "activities": c.activities.select_related("created_by"), "page_title": c.case_id})
