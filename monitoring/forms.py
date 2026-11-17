from django import forms

from core.forms import StyledModelForm, StyledForm, DateInput
from projects.models import Project
from .models import MonitoringVisit, ProgressUpdate, ProjectEvaluation

SCORES = [(i, f"{i} — {l}") for i, l in [(1, "Very poor"), (2, "Poor"), (3, "Fair"), (4, "Good"), (5, "Excellent")]]


class VisitForm(StyledModelForm):
    class Meta:
        model = MonitoringVisit
        fields = ["visit_date", "notes"]
        widgets = {"visit_date": DateInput(), "notes": forms.Textarea(attrs={"rows": 5})}


class ProgressUpdateForm(StyledModelForm):
    photo = forms.ImageField(required=False, label="Evidence photo (optional)")
    photo_caption = forms.CharField(required=False, max_length=255, label="Photo caption")

    class Meta:
        model = ProgressUpdate
        fields = ["date", "progress_percentage", "activities_completed", "activities_remaining", "challenges", "recommendations"]
        widgets = {"date": DateInput()}
        labels = {"progress_percentage": "Overall progress (%)"}

    def clean_progress_percentage(self):
        v = self.cleaned_data["progress_percentage"]
        if v > 100:
            raise forms.ValidationError("Progress cannot be more than 100%.")
        return v

    def clean_photo(self):
        f = self.cleaned_data.get("photo")
        from django.conf import settings
        if f and f.size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise forms.ValidationError(f"Photo is larger than {settings.MAX_UPLOAD_SIZE_MB} MB.")
        return f


class ReviewForm(StyledForm):
    decision = forms.ChoiceField(choices=[("approved", "Approve update"), ("changes_requested", "Request changes")])
    comments = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4}))

    def clean(self):
        d = super().clean()
        if d.get("decision") == "changes_requested" and not (d.get("comments") or "").strip():
            self.add_error("comments", "Explain what must be corrected.")
        return d


class EvaluationForm(StyledModelForm):
    class Meta:
        model = ProjectEvaluation
        fields = ["evaluation_date", "relevance", "effectiveness", "efficiency", "sustainability", "findings", "lessons_learned", "recommendations"]
        widgets = {"evaluation_date": DateInput(), "findings": forms.Textarea(attrs={"rows": 4}),
                   "lessons_learned": forms.Textarea(attrs={"rows": 3}), "recommendations": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        for f in ("relevance", "effectiveness", "efficiency", "sustainability"):
            self.fields[f] = forms.TypedChoiceField(choices=SCORES, coerce=int, initial=3, widget=forms.Select(attrs={"class": "form-select"}))
