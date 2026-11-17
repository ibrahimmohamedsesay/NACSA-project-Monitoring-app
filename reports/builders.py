"""Report builders. Every report returns (title, columns, rows, summary) from live
database queries; nothing is hard-coded. `f` is a dict of filter values."""
import datetime
from decimal import Decimal

from django.db.models import Count, Sum, Q

from beneficiaries.models import Beneficiary, BeneficiaryProject
from finance.models import Payment
from grm.models import GRMCase
from monitoring.models import ProgressUpdate
from projects.models import Project
from results.models import ResultIndicator

REPORTS = {
    "project": ("Project register", "All registered projects with status, budget and progress."),
    "progress": ("Progress report", "Verified progress per active project, with the latest approved update."),
    "district": ("District summary", "Projects, budget and progress grouped by district."),
    "beneficiary": ("Beneficiary report", "Beneficiaries by project, sex, community and service status."),
    "me": ("M&E / results report", "Indicator baseline, target, current value and achievement."),
    "finance": ("Finance report", "Payments to beneficiaries by project and status."),
    "grm": ("Grievance report", "Grievance cases by category, status and project."),
    "delayed": ("Delayed & at-risk projects", "Projects past their due date or flagged at risk."),
    "completed": ("Completed projects", "Projects delivered, with budget and dates."),
    "monthly": ("Monthly summary", "Activity in the selected month."),
    "quarterly": ("Quarterly summary", "Activity in the selected quarter."),
    "annual": ("Annual summary", "Activity in the selected year."),
}


def _d(v):
    try:
        return datetime.date.fromisoformat(v) if v else None
    except ValueError:
        return None


def _projects(f):
    qs = Project.objects.filter(is_archived=False).select_related("officer")
    if f.get("district"):
        qs = qs.filter(district=f["district"])
    if f.get("status"):
        qs = qs.filter(status=f["status"])
    if f.get("project"):
        qs = qs.filter(pk=f["project"])
    if f.get("type"):
        qs = qs.filter(project_type=f["type"])
    if _d(f.get("from")):
        qs = qs.filter(start_date__gte=_d(f["from"]))
    if _d(f.get("to")):
        qs = qs.filter(start_date__lte=_d(f["to"]))
    return qs


def _n(v):
    return f"{Decimal(v or 0):,.2f}"


def period_range(kind, f):
    today = datetime.date.today()
    y = int(f.get("year") or today.year)
    if kind == "monthly":
        m = int(f.get("month") or today.month)
        start = datetime.date(y, m, 1)
        end = (datetime.date(y + (m == 12), (m % 12) + 1, 1)) - datetime.timedelta(days=1)
        return start, end, start.strftime("%B %Y")
    if kind == "quarterly":
        q = int(f.get("quarter") or ((today.month - 1) // 3 + 1))
        start = datetime.date(y, 3 * q - 2, 1)
        em = 3 * q
        end = datetime.date(y + (em == 12), (em % 12) + 1, 1) - datetime.timedelta(days=1)
        return start, end, f"Q{q} {y}"
    return datetime.date(y, 1, 1), datetime.date(y, 12, 31), str(y)


def build(kind, f):
    title = REPORTS[kind][0]
    if kind == "project":
        rows = [[p.project_id, p.name, p.project_type, p.district, p.get_status_display(), p.health, f"{p.completion_percentage}%", _n(p.budget), p.start_date.isoformat(), p.expected_completion_date.isoformat(), str(p.officer or "—")] for p in _projects(f)]
        cols = ["ID", "Project", "Type", "District", "Status", "Health", "Progress", "Budget (NLe)", "Start", "Due", "Officer"]
        tot = sum(Decimal(r[7].replace(",", "")) for r in rows)
        return title, cols, rows, [("Projects", len(rows)), ("Total budget (NLe)", _n(tot))]
    if kind == "progress":
        rows = []
        for p in _projects(f).filter(status__in=["ongoing", "at_risk", "delayed", "planned", "completed"]):
            u = p.progress_updates.filter(review_status="approved").order_by("-date").first()
            rows.append([p.project_id, p.name, p.district, f"{p.completion_percentage}%", p.health, u.date.isoformat() if u else "No approved update", (u.challenges[:90] if u else "")])
        avg = round(sum(int(r[3][:-1]) for r in rows) / len(rows), 1) if rows else 0
        return title, ["ID", "Project", "District", "Progress", "Health", "Last verified", "Challenges"], rows, [("Projects", len(rows)), ("Average progress", f"{avg}%")]
    if kind == "district":
        rows = []
        for r in _projects(f).values("district").annotate(n=Count("id"), b=Sum("budget"), done=Count("id", filter=Q(status="completed")), delayed=Count("id", filter=Q(status="delayed"))).order_by("district"):
            ps = _projects(f).filter(district=r["district"])
            avg = round(sum(p.completion_percentage for p in ps) / max(ps.count(), 1))
            rows.append([r["district"], r["n"], r["done"], r["delayed"], f"{avg}%", _n(r["b"])])
        return title, ["District", "Projects", "Completed", "Delayed", "Avg progress", "Budget (NLe)"], rows, [("Districts", len(rows)), ("Projects", sum(r[1] for r in rows))]
    if kind == "beneficiary":
        qs = BeneficiaryProject.objects.select_related("beneficiary", "project")
        if f.get("project"):
            qs = qs.filter(project_id=f["project"])
        if f.get("district"):
            qs = qs.filter(project__district=f["district"])
        if f.get("status"):
            qs = qs.filter(status=f["status"]) if f["status"] in ("targeted", "enrolled", "serviced") else qs
        rows = [[l.beneficiary.name, l.beneficiary.get_sex_display(), l.beneficiary.age or "—", l.beneficiary.community, l.project.project_id, l.get_status_display(), l.support_type or "—"] for l in qs.order_by("project__project_id", "beneficiary__name")]
        f_ = sum(1 for r in rows if r[1] == "Female")
        return title, ["Name", "Sex", "Age", "Community", "Project", "Status", "Support"], rows, [("Records", len(rows)), ("Female", f_), ("Male", len(rows) - f_)]
    if kind == "me":
        qs = ResultIndicator.objects.select_related("project")
        if f.get("project"):
            qs = qs.filter(project_id=f["project"])
        if f.get("district"):
            qs = qs.filter(project__district=f["district"])
        rows = [[i.project.project_id, i.name, i.get_indicator_type_display(), i.baseline, i.target, i.current_value, f"{i.achievement_percentage}%", i.get_status_display()] for i in qs]
        ach = sum(1 for i in qs if i.status == "achieved")
        return title, ["Project", "Indicator", "Type", "Baseline", "Target", "Current", "Achievement", "Status"], rows, [("Indicators", len(rows)), ("Achieved", ach)]
    if kind == "finance":
        qs = Payment.objects.select_related("beneficiary_project__beneficiary", "beneficiary_project__project")
        if f.get("project"):
            qs = qs.filter(beneficiary_project__project_id=f["project"])
        if f.get("district"):
            qs = qs.filter(beneficiary_project__project__district=f["district"])
        if f.get("status") in ("pending", "processing", "paid", "failed"):
            qs = qs.filter(status=f["status"])
        if _d(f.get("from")):
            qs = qs.filter(created_at__date__gte=_d(f["from"]))
        if _d(f.get("to")):
            qs = qs.filter(created_at__date__lte=_d(f["to"]))
        rows = [[p.beneficiary_project.project.project_id, p.beneficiary_project.beneficiary.name, _n(p.amount), p.get_status_display(), p.paid_date.isoformat() if p.paid_date else "—"] for p in qs]
        paid = qs.filter(status="paid").aggregate(s=Sum("amount"))["s"]
        pend = qs.exclude(status="paid").aggregate(s=Sum("amount"))["s"]
        return title, ["Project", "Beneficiary", "Amount (NLe)", "Status", "Paid date"], rows, [("Payments", len(rows)), ("Paid (NLe)", _n(paid)), ("Not yet paid (NLe)", _n(pend))]
    if kind == "grm":
        qs = GRMCase.objects.select_related("project", "assigned_to")
        if f.get("project"):
            qs = qs.filter(project_id=f["project"])
        if f.get("district"):
            qs = qs.filter(project__district=f["district"])
        if f.get("status") in ("open", "under_review", "resolved", "closed"):
            qs = qs.filter(status=f["status"])
        if _d(f.get("from")):
            qs = qs.filter(created_at__date__gte=_d(f["from"]))
        if _d(f.get("to")):
            qs = qs.filter(created_at__date__lte=_d(f["to"]))
        rows = [[c.case_id, c.project.project_id if c.project else "—", c.complainant, c.category, c.get_status_display(), str(c.assigned_to or "—"), c.created_at.date().isoformat()] for c in qs]
        res = qs.filter(status__in=["resolved", "closed"]).count()
        return title, ["Case", "Project", "Complainant", "Category", "Status", "Assigned", "Opened"], rows, [("Cases", len(rows)), ("Resolved/closed", res)]
    if kind == "delayed":
        ps = [p for p in _projects(f).exclude(status__in=["completed", "draft", "rejected", "submitted", "under_review"]) if p.health in ("Delayed", "At risk")]
        today = datetime.date.today()
        rows = [[p.project_id, p.name, p.district, p.health, f"{p.completion_percentage}%", p.expected_completion_date.isoformat(), max((today - p.expected_completion_date).days, 0), str(p.officer or "—")] for p in ps]
        return title, ["ID", "Project", "District", "Health", "Progress", "Due", "Days overdue", "Officer"], rows, [("Projects", len(rows))]
    if kind == "completed":
        qs = _projects(f).filter(status="completed")
        rows = [[p.project_id, p.name, p.district, _n(p.budget), p.start_date.isoformat(), p.expected_completion_date.isoformat(), p.target_beneficiaries] for p in qs]
        return title, ["ID", "Project", "District", "Budget (NLe)", "Start", "Due", "Target beneficiaries"], rows, [("Completed", len(rows)), ("Budget (NLe)", _n(qs.aggregate(s=Sum("budget"))["s"]))]
    # period summaries
    s, e, label = period_range(kind, f)
    title = f"{title} — {label}"
    rows = [
        ["Projects registered", Project.objects.filter(created_at__date__range=(s, e)).count()],
        ["Projects completed", Project.objects.filter(status="completed", updated_at__date__range=(s, e)).count()],
        ["Progress updates submitted", ProgressUpdate.objects.filter(date__range=(s, e)).count()],
        ["Progress updates approved", ProgressUpdate.objects.filter(date__range=(s, e), review_status="approved").count()],
        ["Beneficiaries registered", Beneficiary.objects.filter(created_at__date__range=(s, e)).count()],
        ["Payments made", Payment.objects.filter(status="paid", paid_date__range=(s, e)).count()],
        ["Amount paid (NLe)", _n(Payment.objects.filter(status="paid", paid_date__range=(s, e)).aggregate(x=Sum("amount"))["x"])],
        ["Grievances received", GRMCase.objects.filter(created_at__date__range=(s, e)).count()],
        ["Grievances resolved", GRMCase.objects.filter(status__in=["resolved", "closed"], updated_at__date__range=(s, e)).count()],
    ]
    return title, ["Measure", "Value"], rows, [("Period", f"{s:%d %b %Y} – {e:%d %b %Y}")]


def data_quality():
    """Simple data-quality checks shown to Admin / M&E / Management."""
    checks = []
    ps = Project.objects.filter(is_archived=False)
    checks.append(("Projects with no assigned officer", ps.filter(officer__isnull=True).exclude(status__in=["draft", "rejected"]).count(), "projects"))
    checks.append(("Projects with no GPS coordinates", ps.filter(gps_coordinates="").count(), "projects"))
    checks.append(("Active projects with no approved update in 60 days", sum(1 for p in ps.filter(status__in=["ongoing", "at_risk", "delayed"]) if not p.progress_updates.filter(review_status="approved", date__gte=datetime.date.today() - datetime.timedelta(days=60)).exists()), "projects"))
    checks.append(("Projects past due date but not completed", sum(1 for p in ps if p.is_overdue), "projects"))
    checks.append(("Beneficiaries with no contact number", Beneficiary.objects.filter(contact_number="").count(), "beneficiaries"))
    checks.append(("Beneficiaries with no age recorded", Beneficiary.objects.filter(age__isnull=True).count(), "beneficiaries"))
    checks.append(("Active projects with no indicators", ps.filter(status__in=["ongoing", "at_risk", "delayed", "completed"], indicators__isnull=True).count(), "results"))
    checks.append(("Progress updates waiting more than 7 days for review", ProgressUpdate.objects.filter(review_status="pending_review", created_at__lt=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)).count(), "monitoring"))
    return checks
