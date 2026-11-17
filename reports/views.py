import csv
import datetime
import io

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, Http404
from django.shortcuts import render

from audit.utils import log
from core.permissions import can, can_report, is_admin, module_required
from core.utils import DISTRICTS, PROJECT_TYPES
from projects.models import Project
from . import builders


@module_required("reports", "view")
def index(request):
    allowed = [(k, v[0], v[1]) for k, v in builders.REPORTS.items() if can_report(request.user, k)]
    show_quality = is_admin(request.user) or request.user.role_name in ("me_officer", "management")
    return render(request, "reports/index.html", {"reports": allowed, "page_title": "Reports & analytics", "show_quality": show_quality})


@module_required("reports", "view")
def quality(request):
    if not (is_admin(request.user) or request.user.role_name in ("me_officer", "management")):
        raise PermissionDenied
    return render(request, "reports/quality.html", {"checks": builders.data_quality(), "page_title": "Data quality"})


def _filters(request):
    return {k: request.GET.get(k, "") for k in ("district", "status", "project", "type", "from", "to", "year", "month", "quarter")}


@module_required("reports", "view")
def run(request, kind):
    if kind not in builders.REPORTS:
        raise Http404
    if not can_report(request.user, kind):
        raise PermissionDenied
    f = _filters(request)
    fmt = request.GET.get("format", "")
    if not (request.GET.get("run") or fmt):
        return render(request, "reports/filter.html", _ctx(kind, f, request))
    title, cols, rows, summary = builders.build(kind, f)
    if fmt in ("excel", "pdf", "csv"):
        log(request.user, f"export_{fmt}", "reports", kind, f"Exported {title} ({len(rows)} rows)")
        return {"excel": _excel, "pdf": _pdf, "csv": _csv}[fmt](title, cols, rows, summary, request)
    log(request.user, "generate", "reports", kind, f"Generated {title} ({len(rows)} rows)")
    ctx = _ctx(kind, f, request)
    ctx.update(title=title, cols=cols, rows=rows, summary=summary, result=True, generated=datetime.datetime.now(), qs=request.GET.urlencode())
    return render(request, "reports/result.html", ctx)


def _ctx(kind, f, request):
    return {"kind": kind, "f": f, "page_title": builders.REPORTS[kind][0], "meta": builders.REPORTS[kind],
            "districts": DISTRICTS, "types": PROJECT_TYPES, "statuses": Project.STATUS_CHOICES,
            "projects": Project.objects.filter(is_archived=False).order_by("project_id"), "years": range(datetime.date.today().year - 3, datetime.date.today().year + 1),
            "months": [(i, datetime.date(2000, i, 1).strftime("%B")) for i in range(1, 13)], "period": kind in ("monthly", "quarterly", "annual")}


def _csv(title, cols, rows, summary, request):
    r = HttpResponse(content_type="text/csv")
    r["Content-Disposition"] = f'attachment; filename="{_fname(title)}.csv"'
    w = csv.writer(r)
    w.writerow(cols)
    for row in rows:
        w.writerow([_safe(c) for c in row])
    return r


def _safe(v):
    """Prevent spreadsheet formula injection from user-entered text."""
    s = str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@") and not s.replace("-", "").replace(".", "").replace(",", "").isdigit() else v


def _fname(title):
    return "".join(c if c.isalnum() else "_" for c in title)[:60] + "_" + datetime.date.today().isoformat()


def _excel(title, cols, rows, summary, request):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    wb = Workbook()
    ws = wb.active
    ws.title = "Report"[:31]
    ws.append([f"NaCSA CPMMS — {title}"])
    ws["A1"].font = Font(bold=True, size=14, color="123B6D")
    ws.append([f"Generated {datetime.datetime.now():%d %b %Y %H:%M} by {request.user.get_full_name() or request.user.username} · DEMO DATA"])
    ws.append([])
    ws.append(cols)
    for c in ws[4]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="123B6D")
        c.alignment = Alignment(wrap_text=True, vertical="center")
    for row in rows:
        ws.append([_safe(c) for c in row])
    ws.append([])
    for k, v in summary:
        ws.append([k, v])
        ws.cell(ws.max_row, 1).font = Font(bold=True)
    for i, col in enumerate(ws.columns, 1):
        width = max((len(str(c.value)) for c in col[3:] if c.value is not None), default=10)
        ws.column_dimensions[ws.cell(4, i).column_letter].width = min(max(width + 2, 12), 48)
    ws.freeze_panes = "A5"
    buf = io.BytesIO()
    wb.save(buf)
    r = HttpResponse(buf.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    r["Content-Disposition"] = f'attachment; filename="{_fname(title)}.xlsx"'
    return r


def _pdf(title, cols, rows, summary, request):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from xml.sax.saxutils import escape
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm, bottomMargin=14 * mm, title=title)
    ss = getSampleStyleSheet()
    cell = ParagraphStyle("c", parent=ss["Normal"], fontSize=7.5, leading=9)
    head = ParagraphStyle("h", parent=cell, textColor=colors.white, fontName="Helvetica-Bold")
    story = [Paragraph(f"<b>NaCSA Community Project Management &amp; Monitoring System</b>", ss["Title"]),
             Paragraph(escape(title), ss["Heading2"]),
             Paragraph(f"Generated {datetime.datetime.now():%d %b %Y %H:%M} by {escape(request.user.get_full_name() or request.user.username)} · DEMO DATA", ss["Normal"]), Spacer(1, 6)]
    for k, v in summary:
        story.append(Paragraph(f"<b>{escape(str(k))}:</b> {escape(str(v))}", ss["Normal"]))
    story.append(Spacer(1, 8))
    data = [[Paragraph(escape(str(c)), head) for c in cols]] + [[Paragraph(escape(str(c)), cell) for c in r] for r in rows[:2000]]
    t = Table(data, repeatRows=1, colWidths=None)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123B6D")), ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
                           ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F8FB")]), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(t)

    def footer(c, d):
        c.setFont("Helvetica", 7)
        c.drawString(12 * mm, 7 * mm, "NaCSA CPMMS prototype — demo data")
        c.drawRightString(landscape(A4)[0] - 12 * mm, 7 * mm, f"Page {d.page}")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    r = HttpResponse(buf.getvalue(), content_type="application/pdf")
    r["Content-Disposition"] = f'attachment; filename="{_fname(title)}.pdf"'
    return r
