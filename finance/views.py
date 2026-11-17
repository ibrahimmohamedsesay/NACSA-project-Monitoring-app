from decimal import Decimal

from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from audit.utils import log
from core.permissions import module_required
from core.utils import paginate
from projects.models import Project
from .forms import PaymentForm
from .models import Payment


@module_required("finance", "view")
def dashboard(request):
    ps = Payment.objects.all()
    agg = {r["status"]: (r["n"], r["t"] or Decimal(0)) for r in ps.values("status").annotate(n=Count("id"), t=Sum("amount"))}
    z = (0, Decimal(0))
    by_project = Project.objects.filter(is_archived=False).annotate(
        paid=Sum("beneficiary_links__payments__amount", filter=Q(beneficiary_links__payments__status="paid")),
        pending=Sum("beneficiary_links__payments__amount", filter=~Q(beneficiary_links__payments__status="paid"))).filter(Q(paid__gt=0) | Q(pending__gt=0)).order_by("-paid")[:10]
    return render(request, "finance/dashboard.html", {
        "page_title": "Finance & payments", "paid": agg.get("paid", z), "pending": agg.get("pending", z),
        "processing": agg.get("processing", z), "failed": agg.get("failed", z), "by_project": by_project,
        "budget": Project.objects.filter(is_archived=False).aggregate(s=Sum("budget"))["s"] or 0,
        "recent": ps.select_related("beneficiary_project__beneficiary", "beneficiary_project__project")[:8]})


@module_required("finance", "view")
def payment_list(request):
    g = request.GET
    qs = Payment.objects.select_related("beneficiary_project__beneficiary", "beneficiary_project__project")
    if g.get("status"):
        qs = qs.filter(status=g["status"])
    if g.get("project"):
        qs = qs.filter(beneficiary_project__project_id=g["project"])
    if g.get("q"):
        qs = qs.filter(beneficiary_project__beneficiary__name__icontains=g["q"])
    if g.get("from"):
        qs = qs.filter(created_at__date__gte=g["from"])
    if g.get("to"):
        qs = qs.filter(created_at__date__lte=g["to"])
    total = qs.aggregate(s=Sum("amount"))["s"] or 0
    page, params = paginate(request, qs)
    return render(request, "finance/list.html", {"page": page, "params": params, "g": g, "total": total, "page_title": "Payments",
                                                 "statuses": Payment.STATUS_CHOICES, "projects": Project.objects.filter(beneficiary_links__payments__isnull=False).distinct()})


@module_required("finance", "add")
def payment_create(request):
    initial = {}
    if request.GET.get("bp"):
        initial["beneficiary_project"] = request.GET["bp"]
    form = PaymentForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        p = form.save()
        log(request.user, "create", "finance", p.pk, f"Payment NLe {p.amount} ({p.status}) for {p.beneficiary_project.project.project_id}")
        messages.success(request, "Payment recorded.")
        return redirect("finance:list")
    return render(request, "generic_form.html", {"form": form, "page_title": "Record payment", "cancel_url": "/finance/payments/"})


@module_required("finance", "edit")
def payment_edit(request, pk):
    p = get_object_or_404(Payment, pk=pk)
    form = PaymentForm(request.POST or None, instance=p)
    if request.method == "POST" and form.is_valid():
        form.save()
        log(request.user, "update", "finance", p.pk, f"Payment #{p.pk} → {p.status}")
        messages.success(request, "Payment updated.")
        return redirect("finance:list")
    return render(request, "generic_form.html", {"form": form, "page_title": "Update payment", "cancel_url": "/finance/payments/"})
