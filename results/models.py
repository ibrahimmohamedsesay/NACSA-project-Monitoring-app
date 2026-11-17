from django.db import models

from core.models import TimeStampedModel
from projects.models import Project


class ResultIndicator(TimeStampedModel):
    """A single Results Framework indicator tracked against a project."""

    OUTPUT = "output"
    OUTCOME = "outcome"

    TYPE_CHOICES = [
        (OUTPUT, "Output"),
        (OUTCOME, "Outcome"),
    ]

    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    ACHIEVED = "achieved"
    OFF_TRACK = "off_track"

    STATUS_CHOICES = [
        (ON_TRACK, "On Track"),
        (AT_RISK, "At Risk"),
        (ACHIEVED, "Achieved"),
        (OFF_TRACK, "Off Track"),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="indicators")
    name = models.CharField(max_length=255)
    indicator_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=OUTPUT)
    baseline = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    target = models.DecimalField(max_digits=12, decimal_places=2)
    current_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reporting_period = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=ON_TRACK)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["project", "name"]

    def __str__(self):
        return f"{self.project.project_id}: {self.name}"

    @property
    def achievement_percentage(self):
        if not self.target:
            return 0
        return round(float(self.current_value) / float(self.target) * 100, 1)
