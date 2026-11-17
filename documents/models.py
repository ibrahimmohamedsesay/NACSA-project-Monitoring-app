from django.conf import settings
from django.db import models

from core.models import TimeStampedModel
from projects.models import Project
from monitoring.models import ProgressUpdate


def document_upload_path(instance, filename):
    return f"documents/project_{instance.project_id}/{filename}"


def evidence_upload_path(instance, filename):
    return f"evidence/project_{instance.project_id}/{filename}"


class Document(TimeStampedModel):
    """A project document (proposal, budget, contract, report, etc.)."""

    PROPOSAL = "proposal"
    BUDGET = "budget"
    CONTRACT = "contract"
    PROGRESS_REPORT = "progress_report"
    MONITORING_REPORT = "monitoring_report"
    COMPLETION_REPORT = "completion_report"
    PHOTOGRAPH = "photograph"
    SUPPORTING_DOCUMENT = "supporting_document"

    CATEGORY_CHOICES = [
        (PROPOSAL, "Project Proposal"),
        (BUDGET, "Budget"),
        (CONTRACT, "Contract"),
        (PROGRESS_REPORT, "Progress Report"),
        (MONITORING_REPORT, "Monitoring Report"),
        (COMPLETION_REPORT, "Completion Report"),
        (PHOTOGRAPH, "Photograph"),
        (SUPPORTING_DOCUMENT, "Supporting Document"),
    ]

    PUBLIC = "public"
    RESTRICTED = "restricted"

    ACCESS_CHOICES = [
        (PUBLIC, "Public"),
        (RESTRICTED, "Restricted"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="documents")
    update = models.ForeignKey(
        ProgressUpdate,
        on_delete=models.SET_NULL,
        related_name="documents",
        null=True,
        blank=True,
    )
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    file = models.FileField(upload_to=document_upload_path)
    access_level = models.CharField(max_length=20, choices=ACCESS_CHOICES, default=PUBLIC)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="uploaded_documents"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.project.project_id}: {self.file.name.split('/')[-1]}"

    @property
    def file_type(self):
        name = self.file.name
        return name.rsplit(".", 1)[-1].upper() if "." in name else ""


class Evidence(TimeStampedModel):
    """A photograph or visual evidence item linked to a project's implementation."""

    BEFORE = "before"
    DURING = "during"
    AFTER = "after"

    PHASE_CHOICES = [
        (BEFORE, "Before"),
        (DURING, "During"),
        (AFTER, "After"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="evidence_items")
    update = models.ForeignKey(
        ProgressUpdate,
        on_delete=models.SET_NULL,
        related_name="evidence_items",
        null=True,
        blank=True,
    )
    image = models.ImageField(upload_to=evidence_upload_path)
    caption = models.CharField(max_length=255, blank=True)
    phase = models.CharField(max_length=10, choices=PHASE_CHOICES, default=DURING)
    monitoring_date = models.DateField(null=True, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="uploaded_evidence"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Evidence"

    def __str__(self):
        return f"{self.project.project_id}: {self.get_phase_display()} photo"
