import datetime

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from audit.utils import log
from core.permissions import can, is_admin, module_required
from core.utils import paginate
from documents.models import Evidence
from notifications.utils import notify, users_with_roles
from projects.models import Project
from .forms import EvaluationForm, ProgressUpdateForm, ReviewForm, VisitForm
from .models import MonitoringVisit, ProgressUpdate, ProjectEvaluation

MONITORABLE = ["approved", "planned", "ongoing", "at_risk", "delayed", "suspended", "completed"]


def _project(pk):
    return get_object_or_404(Project, pk=pk, is_archived=False)


@module_required("monitoring", "view")
def dashboard(request):
    u = request.user
    today = datetime.date.today()
    updates = ProgressUpdate.objects.select_related("project", "officer")
    ctx = {
        "page_title": "Monitoring & M&E",
        "pending": updates.filter(review_status="pending_review").count(),
        "changes": updates.filter(review_status="changes_requested").count(),
        "visits_30": MonitoringVisit.objects.filter(visit_date__gte=today - datetime.timedelta(days=30)).count(),
        "avg_score": ProjectEvaluation.objects.all(),
        "recent_updates": updates.order_by("-created_at")[:8],
        "recent_visits": MonitoringVisit.objects.select_related("project", "officer")[:6],
        "recent_eval": ProjectEvaluation.objects.select_related("project", "evaluator")[:6],
        "no_update": [p for p in Project.objects.filter(status__in=["ongoing", "at_risk", "delayed"], is_archived=False)
                      if not p.progress_updates.filter(date__gte=today - datetime.timedelta(days=30)).exists()][:8],
    }
    scores = ProjectEvaluation.objects.all()
    ctx["avg_score"] = round(sum(e.average_score for e in scores) / scores.count(), 1) if scores else None
    ctx["can_review"] = can(u, "monitoring", "review")
    return render(request, "monitoring/dashboard.html", ctx)


@module_required("monitoring", "view")
def update_list(request):
    qs = ProgressUpdate.objects.select_related("project", "officer", "reviewed_by")
    s = request.GET.get("status", "")
    if s:
        qs = qs.filter(review_status=s)
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(project__name__icontains=q) | Q(project__project_id__icontains=q))
    if not can(request.user, "monitoring", "review") and request.user.role_name == "field_officer":
        qs = qs.filter(Q(officer=request.user) | Q(project__officer=request.user))
    page, params = paginate(request, qs)
    return render(request, "monitoring/update_list.html", {"page": page, "params": params, "page_title": "Progress updates", "s": s, "q": q,
                                                          "choices": ProgressUpdate.REVIEW_STATUS_CHOICES})


@module_required("monitoring", "add")
def update_create(request, pk):
    p = _project(pk)
    if p.status not in MONITORABLE:
        messages.error(request, "Progress can only be reported on approved or active projects.")
        return redirect("projects:detail", pk=p.pk)
    form = ProgressUpdateForm(request.POST or None, request.FILES or None, initial={"date": datetime.date.today(), "progress_percentage": p.completion_percentage})
    if request.method == "POST" and form.is_valid():
        up = form.save(commit=False)
        up.project, up.officer = p, request.user
        up.save()
        photo = form.cleaned_data.get("photo")
        if photo:
            Evidence.objects.create(project=p, update=up, image=photo, caption=form.cleaned_data.get("photo_caption", ""),
                                    phase="during", monitoring_date=up.date, uploaded_by=request.user)
        log(request.user, "create", "monitoring", up.pk, f"Progress update {up.progress_percentage}% on {p.project_id}")
        notify(users_with_roles("me_officer", "project_manager"), "update_submitted", f"New progress update on {p.project_id} ({up.progress_percentage}%) awaits review.", reverse("monitoring:update_review", args=[up.pk]))
        messages.success(request, "Progress update submitted for review.")
        return redirect(reverse("projects:detail", args=[p.pk]) + "?tab=monitoring")
    return render(request, "monitoring/form.html", {"form": form, "p": p, "page_title": "Progress update", "heading": f"Progress update — {p.project_id}", "multipart": True})


@module_required("monitoring", "add")
def visit_create(request, pk):
    p = _project(pk)
    form = VisitForm(request.POST or None, initial={"visit_date": datetime.date.today()})
    if request.method == "POST" and form.is_valid():
        v = form.save(commit=False)
        v.project, v.officer = p, request.user
        v.save()
        log(request.user, "create", "monitoring", v.pk, f"Monitoring visit logged for {p.project_id}")
        messages.success(request, "Monitoring visit saved.")
        return redirect(reverse("projects:detail", args=[p.pk]) + "?tab=monitoring")
    return render(request, "monitoring/form.html", {"form": form, "p": p, "page_title": "Monitoring visit", "heading": f"Log monitoring visit — {p.project_id}"})


@module_required("monitoring", "evaluate")
def evaluation_create(request, pk):
    p = _project(pk)
    form = EvaluationForm(request.POST or None, initial={"evaluation_date": datetime.date.today()})
    if request.method == "POST" and form.is_valid():
        e = form.save(commit=False)
        e.project, e.evaluator = p, request.user
        e.save()
        log(request.user, "create", "monitoring", e.pk, f"Evaluation ({e.average_score}/5) recorded for {p.project_id}")
        messages.success(request, "Evaluation saved.")
        return redirect(reverse("projects:detail", args=[p.pk]) + "?tab=monitoring")
    return render(request, "monitoring/form.html", {"form": form, "p": p, "page_title": "Evaluation", "heading": f"Project evaluation — {p.project_id}"})


@module_required("monitoring", "review")
def update_review(request, pk):
    up = get_object_or_404(ProgressUpdate.objects.select_related("project", "officer"), pk=pk)
    if up.officer_id == request.user.pk and not is_admin(request.user):
        messages.error(request, "You cannot review your own update.")
        return redirect("monitoring:update_list")
    form = ReviewForm(request.POST or None)
    if request.method == "POST" and up.review_status == "pending_review" and form.is_valid():
        d = form.cleaned_data
        up.review_status, up.reviewed_by, up.review_comments = d["decision"], request.user, d["comments"]
        up.save()
        p = up.project
        link = reverse("projects:detail", args=[p.pk]) + "?tab=monitoring"
        if d["decision"] == "approved":
            p.completion_percentage = up.progress_percentage
            if p.status in ("approved", "planned") and up.progress_percentage > 0:
                p.status = "ongoing"
            p.save(update_fields=["completion_percentage", "status", "updated_at"])
            notify([up.officer], "update_approved", f"Your update on {p.project_id} was approved ({up.progress_percentage}%).", link)
        else:
            notify([up.officer], "changes_requested", f"Changes requested on your {p.project_id} update: {d['comments'][:120]}", link)
        log(request.user, d["decision"], "monitoring", up.pk, f"Progress update on {p.project_id}: {d['decision']}")
        messages.success(request, "Review recorded.")
        return redirect("monitoring:update_list")
    return render(request, "monitoring/review.html", {"up": up, "form": form, "evidence": up.evidence_items.all(), "page_title": "Review progress update"})
