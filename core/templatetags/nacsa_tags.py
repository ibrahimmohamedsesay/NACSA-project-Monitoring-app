from django import template
from django.utils.safestring import mark_safe

from core.permissions import can as _can, can_report as _can_report

register = template.Library()

BADGES = {
    # project
    "draft": "grey", "submitted": "info", "under_review": "info", "approved": "green",
    "planned": "blue", "ongoing": "green", "at_risk": "orange", "delayed": "red",
    "completed": "green", "rejected": "red", "suspended": "red",
    # progress review
    "pending_review": "orange", "changes_requested": "orange",
    # beneficiary pipeline
    "targeted": "blue", "enrolled": "info", "serviced": "green",
    # payments
    "pending": "orange", "processing": "info", "paid": "green", "failed": "red",
    "not paid": "grey",
    # grm
    "open": "orange", "resolved": "green", "closed": "grey",
    # indicators
    "on_track": "green", "achieved": "green", "off_track": "red",
    "not_started": "grey", "in_progress": "blue",
    # health
    "on track": "green", "at risk": "orange", "delayed ": "red",
}


@register.simple_tag
def badge(value, label=None):
    key = str(value).lower()
    css = BADGES.get(key, "grey")
    text = label or str(value).replace("_", " ").title()
    return mark_safe(f'<span class="badge badge-{css}">{text}</span>')


@register.simple_tag
def can(user, module, action="view"):
    return _can(user, module, action)


@register.simple_tag
def can_report(user, report_type):
    return _can_report(user, report_type)


@register.filter
def nle(value):
    try:
        return f"NLe {float(value):,.2f}"
    except (TypeError, ValueError):
        return "NLe 0.00"


@register.filter
def get_item(d, key):
    try:
        return d.get(key)
    except AttributeError:
        return None


@register.filter
def pct_color(value):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "red"
    return "green" if v >= 75 else ("blue" if v >= 40 else "orange")


@register.inclusion_tag("partials/_field.html")
def field(bound_field):
    return {"f": bound_field}


@register.inclusion_tag("partials/_pagination.html", takes_context=True)
def pagination(context, page, params=""):
    return {"page": page, "params": params}
