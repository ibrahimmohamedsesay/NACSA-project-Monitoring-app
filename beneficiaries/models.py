from django.db import models

from core.models import TimeStampedModel
from projects.models import Project


class Beneficiary(TimeStampedModel):
    """
    A person or household that receives support from one or more
    projects, linked via BeneficiaryProject. Demo data only — no real
    personal information should ever be entered here (enforced by
    convention/process, not by the schema, per the dissertation scope).
    """

    MALE = "M"
    FEMALE = "F"

    SEX_CHOICES = [(MALE, "Male"), (FEMALE, "Female")]

    name = models.CharField(max_length=255)
    sex = models.CharField(max_length=1, choices=SEX_CHOICES)
    age = models.PositiveSmallIntegerField(null=True, blank=True)
    contact_number = models.CharField(max_length=20, blank=True)
    community = models.CharField(max_length=100, blank=True)
    household_info = models.CharField(max_length=255, blank=True)
    disability_status = models.CharField(max_length=100, blank=True, default="None reported")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class BeneficiaryProject(TimeStampedModel):
    """
    Links a Beneficiary to a Project and tracks where they are in the
    targeting → enrolment → servicing → payment pipeline.
    """

    TARGETED = "targeted"
    ENROLLED = "enrolled"
    SERVICED = "serviced"

    STATUS_CHOICES = [
        (TARGETED, "Targeted"),
        (ENROLLED, "Enrolled"),
        (SERVICED, "Serviced"),
    ]

    beneficiary = models.ForeignKey(
        Beneficiary, on_delete=models.CASCADE, related_name="project_links"
    )
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="beneficiary_links")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=TARGETED)
    support_type = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["beneficiary", "project"]

    def __str__(self):
        return f"{self.beneficiary.name} — {self.project.project_id}"

    @property
    def payment_status(self):
        payment = self.payments.order_by("-created_at").first()
        return payment.status if payment else "Not Paid"
