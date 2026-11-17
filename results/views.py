from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from audit.utils import log
from core.permissions import module_required
from core.utils import paginate
from projects.models import Project
from .forms import IndicatorForm
from .models import ResultIndicator


@module_required("results", "view")
def indicator_list(request):
    qs = ResultIndicator.objects.select_related("project")
    g = request.GET
    if g.get("project"):
        qs = qs.filter(project_id=g["project"])
    if g.get("type"):
        qs = qs.filter(indicator_type=g["type"])
    if g.get("status"):
        qs = qs.filter(status=g["status"])
    if g.get("q"):
        qs = qs.filter(Q(name__icontains=g["q"]) | Q(project__name__icontains=g["q"]))
    counts = {r["status"]: r["n"] for r in ResultIndicator.objects.values("status").annotate(n=Count("id"))}
    page, params = paginate(request, qs)
    return render(request, "results/list.html", {
        "page": page, "params": params, "page_title": "Results framework", "g": g, "counts": counts,
        "projects": Project.objects.filter(indicators__isnull=False).distinct(),
        "types": ResultIndicator.TYPE_CHOICES, "statuses": ResultIndicator.STATUS_CHOICES, "total": ResultIndicator.objects.count()})


@module_required("results", "add")
def indicator_create(request):
    initial = {"project": request.GET.get("project")} if request.GET.get("project") else {}
    form = IndicatorForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        i = form.save()
        log(request.user, "create", "results", i.pk, f"Indicator “{i.name}” added to {i.project.project_id}")
        messages.success(request, "Indicator saved.")
        return redirect("results:list")
    return render(request, "generic_form.html", {"form": form, "page_title": "Add indicator", "cancel_url": "/results/"})


@module_required("results", "edit")
def indicator_edit(request, pk):
    i = get_object_or_404(ResultIndicator, pk=pk)
    form = IndicatorForm(request.POST or None, instance=i)
    if request.method == "POST" and form.is_valid():
        form.save()
        log(request.user, "update", "results", i.pk, f"Indicator “{i.name}” updated (current {i.current_value}/{i.target})")
        messages.success(request, "Indicator updated.")
        return redirect("results:list")
    return render(request, "generic_form.html", {"form": form, "page_title": f"Edit indicator", "cancel_url": "/results/"})
