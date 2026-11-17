from django.conf import settings
from django.db import models

from core.models import TimeStampedModel


class Project(TimeStampedModel):
    """
    A single NaCSA community project, from registration through completion.
    project_id is the human-readable code shown throughout the UI
    (e.g. NACSA-PRJ-014); the numeric primary key is Django's default `id`.
    """

    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    PLANNED = "planned"
    ONGOING = "ongoing"
    AT_RISK = "at_risk"
    DELAYED = "delayed"
    COMPLETED = "completed"
    REJECTED = "rejected"
    SUSPENDED = "suspended"

    STATUS_CHOICES = [
        (DRAFT, "Draft"),
        (SUBMITTED, "Submitted"),
        (UNDER_REVIEW, "Under Review"),
        (APPROVED, "Approved"),
        (PLANNED, "Planned"),
        (ONGOING, "Ongoing"),
        (AT_RISK, "At Risk"),
        (DELAYED, "Delayed"),
        (COMPLETED, "Completed"),
        (REJECTED, "Rejected"),
        (SUSPENDED, "Suspended"),
    ]

    project_id = models.CharField(max_length=20, unique=True, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    project_type = models.CharField(max_length=100, blank=True)

    # Geography
    district = models.CharField(max_length=100)
    chiefdom = models.CharField(max_length=100, blank=True)
    community = models.CharField(max_length=100, blank=True)
    ward = models.CharField(max_length=100, blank=True)
    gps_coordinates = models.CharField(max_length=100, blank=True)

    # Budget & timeline
    budget = models.DecimalField(max_digits=14, decimal_places=2)
    start_date = models.DateField()
    expected_completion_date = models.DateField()

    # People & organisation
    officer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_projects",
        null=True,
        blank=True,
    )
    implementing_organization = models.CharField(max_length=255, blank=True)
    target_beneficiaries = models.PositiveIntegerField(default=0)
    objectives = models.TextField(blank=True)

    # Status & progress
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=DRAFT)
    completion_percentage = models.PositiveSmallIntegerField(default=0)
    is_archived = models.BooleanField(default=False)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_projects",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.project_id} — {self.name}"

    def save(self, *args, **kwargs):
        if not self.project_id:
            self.project_id = self._generate_project_id()
        super().save(*args, **kwargs)

    def _generate_project_id(self):
        last = Project.objects.order_by("id").last()
        next_number = (last.id + 1) if last else 1
        return f"NACSA-PRJ-{next_number:03d}"

    @property
    def is_editable(self):
        return self.status in {self.DRAFT, self.REJECTED}


class ProjectActivity(TimeStampedModel):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

    STATUS_CHOICES = [
        (NOT_STARTED, "Not Started"),
        (IN_PROGRESS, "In Progress"),
        (COMPLETED, "Completed"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="activities")
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=NOT_STARTED)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.project.project_id}: {self.name}"


class ProjectMilestone(TimeStampedModel):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

    STATUS_CHOICES = [
        (PLANNED, "Planned"),
        (IN_PROGRESS, "In Progress"),
        (COMPLETED, "Completed"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="milestones")
    title = models.CharField(max_length=255)
    target_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PLANNED)

    class Meta:
        ordering = ["target_date"]

    def __str__(self):
        return f"{self.project.project_id}: {self.title}"


class ProjectApproval(TimeStampedModel):
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"

    DECISION_CHOICES = [
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
        (CHANGES_REQUESTED, "Changes Requested"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="approvals")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="project_reviews"
    )
    decision = models.CharField(max_length=20, choices=DECISION_CHOICES)
    comments = models.TextField(blank=True)
    decided_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-decided_at"]

    def __str__(self):
        return f"{self.project.project_id} — {self.get_decision_display()} by {self.reviewed_by}"


def _project_health(self):
    """Computed health label shown on lists and the dashboard."""
    import datetime
    today = datetime.date.today()
    if self.status == self.COMPLETED:
        return "Completed"
    if self.status in (self.DRAFT, self.SUBMITTED, self.UNDER_REVIEW, self.REJECTED):
        return "Not started"
    if self.status == self.DELAYED or (self.expected_completion_date < today):
        return "Delayed"
    if self.status == self.AT_RISK:
        return "At risk"
    total_days = max((self.expected_completion_date - self.start_date).days, 1)
    elapsed = max((today - self.start_date).days, 0)
    expected = min(100, elapsed * 100 / total_days)
    if expected - self.completion_percentage > 25:
        return "At risk"
    return "On track"


Project.health = property(_project_health)
Project.is_overdue = property(lambda self: self.status not in (self.COMPLETED, self.REJECTED, self.DRAFT) and self.expected_completion_date < __import__("datetime").date.today())
