from django.conf import settings
from django.db import models

from core.models import TimeStampedModel
from projects.models import Project


class MonitoringVisit(TimeStampedModel):
    """A field monitoring visit to a project site."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="monitoring_visits")
    officer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="monitoring_visits"
    )
    visit_date = models.DateField()
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-visit_date"]

    def __str__(self):
        return f"{self.project.project_id} — visit on {self.visit_date}"


class ProgressUpdate(TimeStampedModel):
    """
    A progress update submitted by a field officer for a project, which
    passes through the review workflow (see ProjectApproval-style review,
    handled in the monitoring views in Phase 8) before it is reflected as
    the project's official completion_percentage.
    """

    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"

    REVIEW_STATUS_CHOICES = [
        (PENDING_REVIEW, "Pending Review"),
        (APPROVED, "Approved"),
        (CHANGES_REQUESTED, "Changes Requested"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="progress_updates")
    officer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="progress_updates"
    )
    date = models.DateField()
    activities_completed = models.TextField(blank=True)
    activities_remaining = models.TextField(blank=True)
    progress_percentage = models.PositiveSmallIntegerField()
    challenges = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    review_status = models.CharField(
        max_length=20, choices=REVIEW_STATUS_CHOICES, default=PENDING_REVIEW
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reviewed_progress_updates",
        null=True,
        blank=True,
    )
    review_comments = models.TextField(blank=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.project.project_id} — {self.progress_percentage}% on {self.date}"


class ProjectEvaluation(TimeStampedModel):
    """Appraisal / evaluation of a project by an M&E officer (scored 1-5)."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="evaluations")
    evaluator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="evaluations"
    )
    evaluation_date = models.DateField()
    relevance = models.PositiveSmallIntegerField(default=3)
    effectiveness = models.PositiveSmallIntegerField(default=3)
    efficiency = models.PositiveSmallIntegerField(default=3)
    sustainability = models.PositiveSmallIntegerField(default=3)
    findings = models.TextField(blank=True)
    lessons_learned = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)

    class Meta:
        ordering = ["-evaluation_date"]

    @property
    def average_score(self):
        return round((self.relevance + self.effectiveness + self.efficiency + self.sustainability) / 4, 1)

    def __str__(self):
        return f"{self.project.project_id} evaluation {self.evaluation_date}"
