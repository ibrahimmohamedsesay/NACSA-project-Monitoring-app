from django import forms
from django.contrib.auth import get_user_model

from core.forms import StyledModelForm, StyledForm, DateInput
from core.utils import DISTRICTS, PROJECT_TYPES
from .models import Project, ProjectActivity, ProjectMilestone, ProjectApproval

User = get_user_model()


class ProjectForm(StyledModelForm):
    district = forms.ChoiceField(choices=[("", "Select district")] + [(d, d) for d in DISTRICTS])
    project_type = forms.ChoiceField(choices=[("", "Select type")] + [(t, t) for t in PROJECT_TYPES], label="Project type")
    initial_activities = forms.CharField(
        required=False, label="Planned activities", widget=forms.Textarea(attrs={"rows": 5}),
        help_text="One activity per line. You can add more later from the project page.")

    class Meta:
        model = Project
        fields = ["name", "project_type", "description", "district", "chiefdom", "community", "ward",
                  "gps_coordinates", "budget", "start_date", "expected_completion_date", "officer",
                  "implementing_organization", "target_beneficiaries", "objectives"]
        widgets = {
            "start_date": DateInput(), "expected_completion_date": DateInput(),
            "description": forms.Textarea(attrs={"rows": 4}), "objectives": forms.Textarea(attrs={"rows": 5}),
            "gps_coordinates": forms.TextInput(attrs={"placeholder": "e.g. 8.4657, -13.2317"}),
        }
        labels = {"officer": "Assigned officer", "expected_completion_date": "Expected completion date",
                  "target_beneficiaries": "Target number of beneficiaries"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["officer"].queryset = User.objects.filter(is_active=True, role__name__in=["field_officer", "project_manager", "me_officer"]).order_by("first_name")
        self.fields["officer"].required = False
        self.fields["officer"].empty_label = "Not assigned yet"
        self.fields["name"].widget.attrs["maxlength"] = 255
        if self.instance.pk:
            del self.fields["initial_activities"]

    def clean_budget(self):
        b = self.cleaned_data["budget"]
        if b is None or b <= 0:
            raise forms.ValidationError("Budget must be greater than zero.")
        return b

    def clean(self):
        d = super().clean()
        s, e = d.get("start_date"), d.get("expected_completion_date")
        if s and e and e < s:
            self.add_error("expected_completion_date", "Completion date cannot be before the start date.")
        return d


class ActivityForm(StyledModelForm):
    class Meta:
        model = ProjectActivity
        fields = ["name", "status"]


class MilestoneForm(StyledModelForm):
    class Meta:
        model = ProjectMilestone
        fields = ["title", "target_date", "status"]
        widgets = {"target_date": DateInput()}


class DecisionForm(StyledModelForm):
    class Meta:
        model = ProjectApproval
        fields = ["decision", "comments"]
        widgets = {"comments": forms.Textarea(attrs={"rows": 4})}

    def clean(self):
        d = super().clean()
        if d.get("decision") in ("rejected", "changes_requested") and not (d.get("comments") or "").strip():
            self.add_error("comments", "Please explain the decision so the project team can act on it.")
        return d
