import datetime
from django import forms
from core.forms import StyledModelForm, DateInput
from beneficiaries.models import BeneficiaryProject
from .models import Payment


class PaymentForm(StyledModelForm):
    class Meta:
        model = Payment
        fields = ["beneficiary_project", "amount", "status", "paid_date"]
        widgets = {"paid_date": DateInput()}
        labels = {"beneficiary_project": "Beneficiary and project"}

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.fields["beneficiary_project"].queryset = BeneficiaryProject.objects.select_related("beneficiary", "project").exclude(project__status__in=["draft", "rejected"]).order_by("project__project_id", "beneficiary__name")
        self.fields["paid_date"].required = False

    def clean_amount(self):
        a = self.cleaned_data["amount"]
        if a is None or a <= 0:
            raise forms.ValidationError("Amount must be greater than zero.")
        return a

    def clean(self):
        d = super().clean()
        if d.get("status") == "paid":
            if not d.get("paid_date"):
                d["paid_date"] = datetime.date.today()
            elif d["paid_date"] > datetime.date.today():
                self.add_error("paid_date", "Paid date cannot be in the future.")
        elif d.get("paid_date"):
            self.add_error("paid_date", "Only paid payments have a paid date.")
        return d
