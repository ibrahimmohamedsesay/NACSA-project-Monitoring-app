import datetime

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from audit.utils import log
from core.permissions import can, is_admin, module_required, role_of
from core.utils import DISTRICTS, PROJECT_TYPES, paginate
from notifications.utils import notify, users_with_roles
from .forms import ActivityForm, DecisionForm, MilestoneForm, ProjectForm
from .models import Project, ProjectActivity, ProjectApproval, ProjectMilestone

LIFECYCLE = ["Plan", "Register", "Review", "Approve", "Implement", "Monitor", "Evaluate", "Report", "Complete", "Archive"]


def lifecycle_stage(p):
    """Index of the current lifecycle step for a project (0-9)."""
    if p.is_archived:
        return 9
    return {"draft": 1, "rejected": 1, "submitted": 2, "under_review": 2, "approved": 3, "planned": 3,
            "ongoing": 5, "at_risk": 5, "delayed": 5, "suspended": 5, "completed": 8}.get(p.status, 1)


def _editable_by(user, project):
    if is_admin(user):
        return not project.is_archived
    return can(user, "projects", "edit") and project.is_editable and not project.is_archived


def _get(pk):
    return get_object_or_404(Project.objects.select_related("officer", "created_by"), pk=pk)


@module_required("projects", "view")
def project_list(request):
    qs = Project.objects.select_related("officer")
    g = request.GET
    if g.get("archived") == "1":
        qs = qs.filter(is_archived=True)
    else:
        qs = qs.filter(is_archived=False)
    q = g.get("q", "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(project_id__icontains=q) | Q(community__icontains=q) | Q(chiefdom__icontains=q) | Q(implementing_organization__icontains=q))
    for key, field in (("status", "status"), ("district", "district"), ("type", "project_type"), ("officer", "officer_id")):
        if g.get(key):
            qs = qs.filter(**{field: g[key]})
    if g.get("from"):
        qs = qs.filter(start_date__gte=g["from"])
    if g.get("to"):
        qs = qs.filter(expected_completion_date__lte=g["to"])
    if g.get("health"):
        ids = [p.pk for p in qs if p.health == g["health"]]
        qs = qs.filter(pk__in=ids)
    sort = g.get("sort", "-created_at")
    if sort.lstrip("-") in {"name", "budget", "completion_percentage", "start_date", "expected_completion_date", "created_at", "project_id"}:
        qs = qs.order_by(sort)
    page, params = paginate(request, qs)
    from django.contrib.auth import get_user_model
    officers = get_user_model().objects.filter(assigned_projects__isnull=False).distinct()
    return render(request, "projects/list.html", {
        "page": page, "params": params, "page_title": "Projects", "districts": DISTRICTS, "types": PROJECT_TYPES,
        "statuses": Project.STATUS_CHOICES, "officers": officers, "g": g, "total": qs.count()})


@module_required("projects", "add")
def project_create(request):
    form = ProjectForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            p = form.save(commit=False)
            p.created_by = request.user
            p.status = Project.DRAFT
            p.save()
            for line in form.cleaned_data.get("initial_activities", "").splitlines():
                if line.strip():
                    ProjectActivity.objects.create(project=p, name=line.strip()[:255])
        log(request.user, "create", "projects", p.pk, f"Registered project {p.project_id} — {p.name}")
        if "submit" in request.POST:
            _submit(request, p)
        else:
            messages.success(request, f"Project {p.project_id} saved as draft.")
        return redirect("projects:detail", pk=p.pk)
    return render(request, "projects/form.html", {"form": form, "page_title": "Register project", "creating": True})


@module_required("projects", "view")
def project_detail(request, pk):
    p = _get(pk)
    u = request.user
    tab = request.GET.get("tab", "overview")
    ctx = {"p": p, "tab": tab, "page_title": p.name, "lifecycle": LIFECYCLE, "stage": lifecycle_stage(p),
           "can_edit": _editable_by(u, p), "can_review": can(u, "projects", "approve") and p.status in ("submitted", "under_review"),
           "can_manage": can(u, "projects", "manage"), "can_submit": (can(u, "projects", "add") or is_admin(u)) and p.status in ("draft",) and not p.is_archived}
    ctx["activities"] = p.activities.all()
    ctx["milestones"] = p.milestones.all()
    ctx["approvals"] = p.approvals.select_related("reviewed_by")
    ctx["act_done"] = ctx["activities"].filter(status="completed").count()
    ctx["act_form"], ctx["ms_form"] = ActivityForm(), MilestoneForm()
    if tab == "monitoring" and can(u, "monitoring", "view"):
        ctx["updates"] = p.progress_updates.select_related("officer")
        ctx["visits"] = p.monitoring_visits.select_related("officer")
        ctx["evaluations"] = p.evaluations.select_related("evaluator")
    if tab == "results" and can(u, "results", "view"):
        ctx["indicators"] = p.indicators.all()
    if tab == "beneficiaries" and can(u, "beneficiaries", "view"):
        ctx["links"] = p.beneficiary_links.select_related("beneficiary")
    if tab == "finance" and can(u, "finance", "view"):
        from finance.models import Payment
        pays = Payment.objects.filter(beneficiary_project__project=p).select_related("beneficiary_project__beneficiary")
        ctx["payments"] = pays
        ctx["paid_total"] = pays.filter(status="paid").aggregate(s=Sum("amount"))["s"] or 0
        ctx["pending_total"] = pays.exclude(status="paid").aggregate(s=Sum("amount"))["s"] or 0
    if tab == "documents":
        docs = p.documents.select_related("uploaded_by")
        if not can(u, "documents", "restricted") and not is_admin(u):
            docs = docs.filter(access_level="public")
        ctx["documents"] = docs
        ctx["evidence"] = p.evidence_items.select_related("uploaded_by")
    if tab == "grm" and can(u, "grm", "view"):
        ctx["cases"] = p.grm_cases.all()
    ctx["tabs"] = [("overview", "Overview", True), ("plan", "Activities & milestones", True),
                   ("monitoring", "Monitoring", can(u, "monitoring", "view")), ("results", "Results", can(u, "results", "view")),
                   ("beneficiaries", "Beneficiaries", can(u, "beneficiaries", "view")), ("finance", "Finance", can(u, "finance", "view")),
                   ("documents", "Documents & evidence", True), ("grm", "Grievances", can(u, "grm", "view")), ("history", "History", True)]
    return render(request, "projects/detail.html", ctx)


@module_required("projects", "view")
def project_edit(request, pk):
    p = _get(pk)
    if not _editable_by(request.user, p):
        raise PermissionDenied
    form = ProjectForm(request.POST or None, instance=p)
    if request.method == "POST" and form.is_valid():
        form.save()
        log(request.user, "update", "projects", p.pk, f"Edited project {p.project_id}")
        if "submit" in request.POST:
            _submit(request, p)
        else:
            messages.success(request, "Project updated.")
        return redirect("projects:detail", pk=p.pk)
    return render(request, "projects/form.html", {"form": form, "p": p, "page_title": f"Edit {p.project_id}"})


def _submit(request, p):
    if p.status not in (Project.DRAFT, Project.REJECTED):
        return
    p.status = Project.SUBMITTED
    p.save(update_fields=["status", "updated_at"])
    log(request.user, "submit", "projects", p.pk, f"Submitted {p.project_id} for approval")
    link = reverse("projects:detail", args=[p.pk])
    notify(users_with_roles("project_manager"), "approval_required", f"{p.project_id} “{p.name}” is waiting for approval.", link)
    notify(users_with_roles("management", "me_officer"), "project_submitted", f"{p.project_id} “{p.name}” was submitted for approval.", link)
    messages.success(request, f"{p.project_id} was submitted for approval.")


@module_required("projects", "view")
@require_POST
def project_submit(request, pk):
    p = _get(pk)
    if not (can(request.user, "projects", "add") or is_admin(request.user)):
        raise PermissionDenied
    if p.status not in (Project.DRAFT, Project.REJECTED):
        messages.error(request, "Only drafts or rejected projects can be submitted.")
    else:
        _submit(request, p)
    return redirect("projects:detail", pk=p.pk)


@module_required("projects", "approve")
def project_review(request, pk):
    p = _get(pk)
    if p.status not in (Project.SUBMITTED, Project.UNDER_REVIEW):
        messages.error(request, "This project is not waiting for a decision.")
        return redirect("projects:detail", pk=p.pk)
    if p.created_by_id == request.user.pk and not is_admin(request.user):
        messages.error(request, "You cannot approve a project you registered yourself. Another approver must decide.")
        return redirect("projects:detail", pk=p.pk)
    if p.status == Project.SUBMITTED:
        p.status = Project.UNDER_REVIEW
        p.save(update_fields=["status", "updated_at"])
    form = DecisionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.save(commit=False)
        d.project, d.reviewed_by = p, request.user
        d.save()
        link = reverse("projects:detail", args=[p.pk])
        if d.decision == "approved":
            p.status = Project.APPROVED
            ev, msg = "project_approved", f"{p.project_id} “{p.name}” was approved."
        elif d.decision == "rejected":
            p.status = Project.REJECTED
            ev, msg = "changes_requested", f"{p.project_id} “{p.name}” was rejected: {d.comments[:120]}"
        else:
            p.status = Project.DRAFT
            ev, msg = "changes_requested", f"Changes requested on {p.project_id}: {d.comments[:120]}"
        p.save(update_fields=["status", "updated_at"])
        log(request.user, d.decision, "projects", p.pk, f"{d.get_decision_display()} — {p.project_id}")
        notify([p.created_by, p.officer], ev, msg, link)
        messages.success(request, f"Decision recorded: {d.get_decision_display()}.")
        return redirect("projects:detail", pk=p.pk)
    return render(request, "projects/review.html", {"p": p, "form": form, "page_title": f"Review {p.project_id}"})


STATUS_ACTIONS = {
    "start": ({"approved", "planned", "suspended"}, "ongoing", "Implementation started"),
    "plan": ({"approved"}, "planned", "Marked as planned"),
    "risk": ({"ongoing", "delayed"}, "at_risk", "Marked at risk"),
    "delay": ({"ongoing", "at_risk"}, "delayed", "Marked delayed"),
    "resume": ({"at_risk", "delayed"}, "ongoing", "Back on track"),
    "suspend": ({"ongoing", "planned", "at_risk", "delayed"}, "suspended", "Suspended"),
    "complete": ({"ongoing", "at_risk", "delayed"}, "completed", "Completed"),
}


@module_required("projects", "manage")
@require_POST
def project_status(request, pk, action):
    p = _get(pk)
    rule = STATUS_ACTIONS.get(action)
    if not rule or p.status not in rule[0]:
        messages.error(request, "That change is not allowed for the project's current status.")
        return redirect("projects:detail", pk=p.pk)
    p.status = rule[1]
    if rule[1] == "completed":
        p.completion_percentage = 100
    p.save(update_fields=["status", "completion_percentage", "updated_at"])
    log(request.user, f"status_{action}", "projects", p.pk, f"{rule[2]}: {p.project_id}")
    notify([p.created_by, p.officer], "project_delayed" if action in ("delay", "risk") else "project_approved", f"{p.project_id}: {rule[2]}.", reverse("projects:detail", args=[p.pk]))
    messages.success(request, f"{p.project_id}: {rule[2]}.")
    return redirect("projects:detail", pk=p.pk)


@require_POST
@module_required("projects", "view")
def project_archive(request, pk):
    if not is_admin(request.user):
        raise PermissionDenied
    p = _get(pk)
    p.is_archived = not p.is_archived
    p.save(update_fields=["is_archived", "updated_at"])
    log(request.user, "archive" if p.is_archived else "restore", "projects", p.pk, f"{'Archived' if p.is_archived else 'Restored'} {p.project_id}")
    messages.success(request, f"{p.project_id} {'archived' if p.is_archived else 'restored'}.")
    return redirect("projects:detail", pk=p.pk)


def _plan_guard(request, p):
    if not (can(request.user, "projects", "edit") or can(request.user, "projects", "manage") or is_admin(request.user)) or p.is_archived:
        raise PermissionDenied


@module_required("projects", "view")
@require_POST
def activity_add(request, pk):
    p = _get(pk)
    _plan_guard(request, p)
    f = ActivityForm(request.POST)
    if f.is_valid():
        a = f.save(commit=False)
        a.project = p
        a.save()
        log(request.user, "create", "projects", p.pk, f"Added activity “{a.name}” to {p.project_id}")
        messages.success(request, "Activity added.")
    else:
        messages.error(request, "Activity name is required.")
    return redirect(reverse("projects:detail", args=[p.pk]) + "?tab=plan")


@module_required("projects", "view")
@require_POST
def activity_status(request, pk, aid):
    p = _get(pk)
    _plan_guard(request, p)
    a = get_object_or_404(ProjectActivity, pk=aid, project=p)
    new = request.POST.get("status")
    if new in dict(ProjectActivity.STATUS_CHOICES):
        a.status = new
        a.save(update_fields=["status", "updated_at"])
        log(request.user, "update", "projects", p.pk, f"Activity “{a.name}” → {a.get_status_display()}")
    return redirect(reverse("projects:detail", args=[p.pk]) + "?tab=plan")


@module_required("projects", "view")
@require_POST
def milestone_add(request, pk):
    p = _get(pk)
    _plan_guard(request, p)
    f = MilestoneForm(request.POST)
    if f.is_valid():
        m = f.save(commit=False)
        m.project = p
        m.save()
        log(request.user, "create", "projects", p.pk, f"Added milestone “{m.title}” to {p.project_id}")
        messages.success(request, "Milestone added.")
    else:
        messages.error(request, "Milestone needs a title and a valid target date.")
    return redirect(reverse("projects:detail", args=[p.pk]) + "?tab=plan")


@module_required("projects", "view")
@require_POST
def milestone_status(request, pk, mid):
    p = _get(pk)
    _plan_guard(request, p)
    m = get_object_or_404(ProjectMilestone, pk=mid, project=p)
    new = request.POST.get("status")
    if new in dict(ProjectMilestone.STATUS_CHOICES):
        m.status = new
        m.save(update_fields=["status", "updated_at"])
        log(request.user, "update", "projects", p.pk, f"Milestone “{m.title}” → {m.get_status_display()}")
    return redirect(reverse("projects:detail", args=[p.pk]) + "?tab=plan")
