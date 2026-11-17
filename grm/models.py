from django.conf import settings
from django.db import models

from core.models import TimeStampedModel
from projects.models import Project


class GRMCase(TimeStampedModel):
    """A grievance redress case, optionally linked to a specific project."""

    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    CLOSED = "closed"

    STATUS_CHOICES = [
        (OPEN, "Open"),
        (UNDER_REVIEW, "Under Review"),
        (RESOLVED, "Resolved"),
        (CLOSED, "Closed"),
    ]

    case_id = models.CharField(max_length=20, unique=True, editable=False)
    project = models.ForeignKey(
        Project, on_delete=models.SET_NULL, related_name="grm_cases", null=True, blank=True
    )
    complainant = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=OPEN)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="assigned_grm_cases",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.case_id} — {self.complainant}"

    def save(self, *args, **kwargs):
        if not self.case_id:
            self.case_id = self._generate_case_id()
        super().save(*args, **kwargs)

    def _generate_case_id(self):
        from datetime import date

        year = date.today().year
        last = GRMCase.objects.order_by("id").last()
        next_number = (last.id + 1) if last else 1
        return f"GRM-{year}-{next_number:03d}"


class GRMActivity(TimeStampedModel):
    """A single logged action in a GRM case's investigation/resolution history."""

    case = models.ForeignKey(GRMCase, on_delete=models.CASCADE, related_name="activities")
    action = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="grm_activities"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "GRM activities"

    def __str__(self):
        return f"{self.case.case_id}: {self.action}"
