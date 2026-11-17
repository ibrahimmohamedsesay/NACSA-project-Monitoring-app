from django import forms
from django.contrib.auth import get_user_model
from core.forms import StyledModelForm, StyledForm
from projects.models import Project
from .models import GRMActivity, GRMCase

CATEGORIES = ["Beneficiary selection", "Payment delay", "Quality of works", "Staff conduct", "Exclusion / targeting", "Land / property", "Other"]


class CaseForm(StyledModelForm):
    category = forms.ChoiceField(choices=[("", "Select category")] + [(c, c) for c in CATEGORIES])

    class Meta:
        model = GRMCase
        fields = ["project", "complainant", "category", "description", "assigned_to"]
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.fields["project"].queryset = Project.objects.filter(is_archived=False).order_by("project_id")
        self.fields["project"].required = False
        self.fields["assigned_to"].queryset = get_user_model().objects.filter(is_active=True, role__name__in=["grm_officer", "project_manager", "me_officer"])
        self.fields["assigned_to"].required = False


class ActivityForm(StyledModelForm):
    new_status = forms.ChoiceField(choices=[("", "Keep current status")] + list(GRMCase.STATUS_CHOICES), required=False, label="Change status")

    class Meta:
        model = GRMActivity
        fields = ["action", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}
