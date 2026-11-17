from django.conf import settings
from django.db import models

from core.models import TimeStampedModel


class Notification(TimeStampedModel):
    """An in-system notification for a single user about a system event."""

    PROJECT_SUBMITTED = "project_submitted"
    APPROVAL_REQUIRED = "approval_required"
    PROJECT_APPROVED = "project_approved"
    CHANGES_REQUESTED = "changes_requested"
    UPDATE_SUBMITTED = "update_submitted"
    UPDATE_APPROVED = "update_approved"
    PROJECT_DELAYED = "project_delayed"
    DEADLINE_APPROACHING = "deadline_approaching"
    DOCUMENT_UPLOADED = "document_uploaded"
    GRM_CASE_UPDATED = "grm_case_updated"

    EVENT_CHOICES = [
        (PROJECT_SUBMITTED, "Project Submitted"),
        (APPROVAL_REQUIRED, "Approval Required"),
        (PROJECT_APPROVED, "Project Approved"),
        (CHANGES_REQUESTED, "Changes Requested"),
        (UPDATE_SUBMITTED, "Monitoring Update Submitted"),
        (UPDATE_APPROVED, "Monitoring Update Approved"),
        (PROJECT_DELAYED, "Project Delayed"),
        (DEADLINE_APPROACHING, "Deadline Approaching"),
        (DOCUMENT_UPLOADED, "Document Uploaded"),
        (GRM_CASE_UPDATED, "GRM Case Updated"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    event_type = models.CharField(max_length=30, choices=EVENT_CHOICES)
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    link = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user}: {self.message[:40]}"
