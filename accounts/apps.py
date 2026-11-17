from django.apps import AppConfig
from django.db.models.signals import post_migrate


def create_roles(sender, **kwargs):
    from .models import Role
    descriptions = {
        "administrator": "Full system access, user management and audit trail.",
        "management": "Oversight: dashboards, reports, finance and GRM summaries.",
        "me_officer": "Monitoring & evaluation: verifies updates, results framework.",
        "project_manager": "Registers, approves and manages projects.",
        "field_officer": "Submits field progress updates, visits and evidence.",
        "finance_officer": "Records and tracks beneficiary payments.",
        "grm_officer": "Registers and resolves grievances.",
        "data_entry_officer": "Registers projects and beneficiaries.",
        "viewer": "Read-only access to non-restricted information.",
    }
    for name, _label in Role.ROLE_CHOICES:
        Role.objects.get_or_create(name=name, defaults={"description": descriptions.get(name, "")})


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        post_migrate.connect(create_roles, sender=self)
