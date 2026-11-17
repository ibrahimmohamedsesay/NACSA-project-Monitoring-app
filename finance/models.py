from django.db import models

from core.models import TimeStampedModel
from beneficiaries.models import BeneficiaryProject


class Payment(TimeStampedModel):
    """A payment made to a beneficiary in connection with a specific project."""

    PENDING = "pending"
    PROCESSING = "processing"
    PAID = "paid"
    FAILED = "failed"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (PROCESSING, "Processing"),
        (PAID, "Paid"),
        (FAILED, "Failed"),
    ]

    beneficiary_project = models.ForeignKey(
        BeneficiaryProject, on_delete=models.CASCADE, related_name="payments"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    paid_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.beneficiary_project.beneficiary.name} — NLE {self.amount} ({self.get_status_display()})"
