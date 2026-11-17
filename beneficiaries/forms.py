from django import forms
from core.forms import StyledModelForm
from projects.models import Project
from .models import Beneficiary, BeneficiaryProject


class BeneficiaryForm(StyledModelForm):
    project = forms.ModelChoiceField(queryset=Project.objects.none(), required=False, label="Enrol in project (optional)")
    support_type = forms.CharField(required=False, max_length=255, label="Support type", help_text="e.g. Cash transfer, Training, Tools")

    class Meta:
        model = Beneficiary
        fields = ["name", "sex", "age", "contact_number", "community", "household_info", "disability_status"]

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.fields["project"].queryset = Project.objects.filter(is_archived=False).exclude(status__in=["draft", "rejected"]).order_by("project_id")
        if self.instance.pk:
            del self.fields["project"], self.fields["support_type"]

    def clean_age(self):
        a = self.cleaned_data.get("age")
        if a is not None and not (0 < a < 120):
            raise forms.ValidationError("Enter a realistic age.")
        return a

    def clean_contact_number(self):
        c = self.cleaned_data.get("contact_number", "").strip()
        if c and not all(ch.isdigit() or ch in "+- ()" for ch in c):
            raise forms.ValidationError("Use digits, spaces, + or - only.")
        return c


class LinkForm(StyledModelForm):
    class Meta:
        model = BeneficiaryProject
        fields = ["project", "status", "support_type"]

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.fields["project"].queryset = Project.objects.filter(is_archived=False).exclude(status__in=["draft", "rejected"]).order_by("project_id")
