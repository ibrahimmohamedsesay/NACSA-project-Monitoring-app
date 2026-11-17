import os
from django import forms
from django.conf import settings
from core.forms import StyledModelForm, DateInput
from projects.models import Project
from .models import Document, Evidence

IMG_EXT = {".jpg", ".jpeg", ".png"}


def _check_size(f):
    if f.size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise forms.ValidationError(f"File is larger than {settings.MAX_UPLOAD_SIZE_MB} MB.")


class DocumentForm(StyledModelForm):
    class Meta:
        model = Document
        fields = ["project", "category", "file", "access_level"]

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.fields["project"].queryset = Project.objects.filter(is_archived=False).order_by("project_id")

    def clean_file(self):
        f = self.cleaned_data["file"]
        ext = os.path.splitext(f.name)[1].lower()
        if ext not in settings.ALLOWED_DOCUMENT_EXTENSIONS:
            raise forms.ValidationError("File type not allowed. Use: " + ", ".join(settings.ALLOWED_DOCUMENT_EXTENSIONS))
        _check_size(f)
        return f


class EvidenceForm(StyledModelForm):
    class Meta:
        model = Evidence
        fields = ["project", "image", "caption", "phase", "monitoring_date"]
        widgets = {"monitoring_date": DateInput()}

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.fields["project"].queryset = Project.objects.filter(is_archived=False).order_by("project_id")

    def clean_image(self):
        f = self.cleaned_data["image"]
        if os.path.splitext(f.name)[1].lower() not in IMG_EXT:
            raise forms.ValidationError("Only JPG or PNG images are accepted.")
        _check_size(f)
        return f
