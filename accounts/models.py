from django.contrib.auth.models import AbstractUser
from django.db import models

from core.models import TimeStampedModel


class Role(TimeStampedModel):
    """
    A user role, e.g. Administrator, Management, M&E Officer, Project
    Manager, Field Officer, Finance Officer, GRM Officer, Data Entry
    Officer, Viewer. Permissions for each role are enforced in views using
    the helpers in core/permissions.py (added in Phase 3), keyed off the
    role name, rather than Django's built-in per-object permission system —
    this keeps the access rules easy to read and matches the fixed set of
    roles described in the dissertation proposal.
    """

    ADMINISTRATOR = "administrator"
    MANAGEMENT = "management"
    ME_OFFICER = "me_officer"
    PROJECT_MANAGER = "project_manager"
    FIELD_OFFICER = "field_officer"
    FINANCE_OFFICER = "finance_officer"
    GRM_OFFICER = "grm_officer"
    DATA_ENTRY_OFFICER = "data_entry_officer"
    VIEWER = "viewer"

    ROLE_CHOICES = [
        (ADMINISTRATOR, "Administrator"),
        (MANAGEMENT, "Management"),
        (ME_OFFICER, "M&E Officer"),
        (PROJECT_MANAGER, "Project Manager"),
        (FIELD_OFFICER, "Field Officer"),
        (FINANCE_OFFICER, "Finance Officer"),
        (GRM_OFFICER, "GRM Officer"),
        (DATA_ENTRY_OFFICER, "Data Entry Officer"),
        (VIEWER, "Viewer"),
    ]

    name = models.CharField(max_length=30, choices=ROLE_CHOICES, unique=True)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.get_name_display()


class User(AbstractUser):
    """
    Custom user model for the NaCSA CPMMS. Extends Django's AbstractUser
    (so username/password/email/first_name/last_name/is_active/etc. are
    already there) with the fields the system actually needs: a role for
    access control, and a department for display purposes on profile and
    user-management screens.
    """

    role = models.ForeignKey(
        Role, on_delete=models.PROTECT, related_name="users", null=True, blank=True
    )
    department = models.CharField(max_length=100, blank=True, default="")
    phone_number = models.CharField(max_length=20, blank=True, default="")

    class Meta:
        ordering = ["first_name", "last_name"]

    def __str__(self):
        full_name = self.get_full_name()
        return full_name if full_name else self.username

    @property
    def role_name(self):
        return self.role.name if self.role else None
