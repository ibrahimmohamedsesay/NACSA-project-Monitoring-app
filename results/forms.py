from core.forms import StyledModelForm
from django import forms
from projects.models import Project
from .models import ResultIndicator


class IndicatorForm(StyledModelForm):
    class Meta:
        model = ResultIndicator
        fields = ["project", "name", "indicator_type", "baseline", "target", "current_value", "reporting_period", "status", "remarks"]
        widgets = {"remarks": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.fields["project"].queryset = Project.objects.filter(is_archived=False).order_by("project_id")

    def clean(self):
        d = super().clean()
        for f in ("baseline", "target", "current_value"):
            if d.get(f) is not None and d[f] < 0:
                self.add_error(f, "Value cannot be negative.")
        if d.get("target") is not None and d["target"] == 0:
            self.add_error("target", "Target must be greater than zero.")
        return d
