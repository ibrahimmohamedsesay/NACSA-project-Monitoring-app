from django.contrib import messages
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from audit.utils import log
from core.permissions import can, module_required
from core.utils import paginate
from projects.models import Project
from .forms import BeneficiaryForm, LinkForm
from .models import Beneficiary, BeneficiaryProject


@module_required("beneficiaries", "view")
def dashboard(request):
    qs = Beneficiary.objects.all()
    total = qs.count()
    sex = {r["sex"]: r["n"] for r in qs.values("sex").annotate(n=Count("id"))}
    ctx = {
        "page_title": "Beneficiaries", "total": total, "female": sex.get("F", 0), "male": sex.get("M", 0),
        "avg_age": qs.aggregate(a=Avg("age"))["a"],
        "disabled": qs.exclude(Q(disability_status__iexact="none reported") | Q(disability_status="") | Q(disability_status__iexact="none")).count(),
        "by_status": {r["status"]: r["n"] for r in BeneficiaryProject.objects.values("status").annotate(n=Count("id"))},
        "by_community": qs.exclude(community="").values("community").annotate(n=Count("id")).order_by("-n")[:8],
        "by_project": Project.objects.annotate(n=Count("beneficiary_links")).filter(n__gt=0).order_by("-n")[:8],
        "recent": qs.order_by("-created_at")[:6],
    }
    return render(request, "beneficiaries/dashboard.html", ctx)


@module_required("beneficiaries", "view")
def beneficiary_list(request):
    g = request.GET
    qs = Beneficiary.objects.all()
    if g.get("q"):
        qs = qs.filter(Q(name__icontains=g["q"]) | Q(community__icontains=g["q"]) | Q(contact_number__icontains=g["q"]))
    if g.get("sex"):
        qs = qs.filter(sex=g["sex"])
    if g.get("project"):
        qs = qs.filter(project_links__project_id=g["project"])
    if g.get("status"):
        qs = qs.filter(project_links__status=g["status"])
    if g.get("community"):
        qs = qs.filter(community__iexact=g["community"])
    qs = qs.distinct().order_by("name")
    page, params = paginate(request, qs)
    return render(request, "beneficiaries/list.html", {
        "page": page, "params": params, "page_title": "Beneficiary register", "g": g, "total": qs.count(),
        "projects": Project.objects.filter(beneficiary_links__isnull=False).distinct(),
        "communities": Beneficiary.objects.exclude(community="").values_list("community", flat=True).distinct().order_by("community"),
        "statuses": BeneficiaryProject.STATUS_CHOICES})


@module_required("beneficiaries", "add")
def beneficiary_create(request):
    form = BeneficiaryForm(request.POST or None, initial={"project": request.GET.get("project")})
    dup = None
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        dup = Beneficiary.objects.filter(name__iexact=d["name"], community__iexact=d["community"]).first()
        if dup and "confirm_duplicate" not in request.POST:
            messages.warning(request, f"A beneficiary named {dup.name} in {dup.community or 'this community'} already exists. Tick “Save anyway” below if this is a different person.")
        else:
            b = form.save()
            proj = d.get("project")
            if proj:
                BeneficiaryProject.objects.get_or_create(beneficiary=b, project=proj, defaults={"support_type": d.get("support_type", ""), "status": "targeted"})
            log(request.user, "create", "beneficiaries", b.pk, f"Registered beneficiary #{b.pk}")
            messages.success(request, "Beneficiary registered.")
            return redirect("beneficiaries:detail", pk=b.pk)
    return render(request, "beneficiaries/form.html", {"form": form, "page_title": "Register beneficiary", "dup": dup})


@module_required("beneficiaries", "view")
def beneficiary_detail(request, pk):
    b = get_object_or_404(Beneficiary, pk=pk)
    links = b.project_links.select_related("project")
    payments = []
    if can(request.user, "finance", "view"):
        from finance.models import Payment
        payments = Payment.objects.filter(beneficiary_project__beneficiary=b).select_related("beneficiary_project__project")
    return render(request, "beneficiaries/detail.html", {"b": b, "links": links, "payments": payments, "link_form": LinkForm(), "page_title": b.name})


@module_required("beneficiaries", "edit")
def beneficiary_edit(request, pk):
    b = get_object_or_404(Beneficiary, pk=pk)
    form = BeneficiaryForm(request.POST or None, instance=b)
    if request.method == "POST" and form.is_valid():
        form.save()
        log(request.user, "update", "beneficiaries", b.pk, f"Updated beneficiary #{b.pk}")
        messages.success(request, "Beneficiary updated.")
        return redirect("beneficiaries:detail", pk=b.pk)
    return render(request, "beneficiaries/form.html", {"form": form, "page_title": f"Edit {b.name}", "b": b})


@module_required("beneficiaries", "add")
@require_POST
def link_add(request, pk):
    b = get_object_or_404(Beneficiary, pk=pk)
    f = LinkForm(request.POST)
    if f.is_valid():
        if BeneficiaryProject.objects.filter(beneficiary=b, project=f.cleaned_data["project"]).exists():
            messages.error(request, "This beneficiary is already linked to that project.")
        else:
            l = f.save(commit=False)
            l.beneficiary = b
            l.save()
            log(request.user, "create", "beneficiaries", b.pk, f"Linked beneficiary #{b.pk} to {l.project.project_id}")
            messages.success(request, "Linked to project.")
    else:
        messages.error(request, "Select a project and status.")
    return redirect("beneficiaries:detail", pk=b.pk)


@module_required("beneficiaries", "view")
@require_POST
def link_status(request, pk):
    l = get_object_or_404(BeneficiaryProject, pk=pk)
    if not (can(request.user, "beneficiaries", "edit") or can(request.user, "beneficiaries", "add")):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    s = request.POST.get("status")
    if s in dict(BeneficiaryProject.STATUS_CHOICES):
        l.status = s
        l.save(update_fields=["status", "updated_at"])
        log(request.user, "update", "beneficiaries", l.beneficiary_id, f"Status → {l.get_status_display()} on {l.project.project_id}")
        messages.success(request, "Status updated.")
    return redirect("beneficiaries:detail", pk=l.beneficiary_id)
