"""
Role-based access control for the NaCSA CPMMS.

Permissions are attached to roles (Sandhu et al., 1996) and every user has
one role. The matrix below is the single source of truth: views, templates
and the REST API all ask `can(user, module, action)`.

Administrator always passes. Restricted data (beneficiary, payment and
finance records) is only open to the roles listed for those modules.
"""
from functools import wraps

from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import LoginRequiredMixin

ADMIN = "administrator"
MGMT = "management"
ME = "me_officer"
PM = "project_manager"
FIELD = "field_officer"
FIN = "finance_officer"
GRM = "grm_officer"
DATA = "data_entry_officer"
VIEWER = "viewer"

ALL_ROLES = {ADMIN, MGMT, ME, PM, FIELD, FIN, GRM, DATA, VIEWER}

PERMISSIONS = {
    "dashboard": {"view": ALL_ROLES},
    "projects": {
        "view": ALL_ROLES,
        "add": {PM, DATA},
        "edit": {PM, DATA},
        "delete": set(),            # administrator only (archive)
        "approve": {PM},            # review / approve / reject
        "manage": {PM},             # activate, complete, suspend
    },
    "monitoring": {
        "view": {MGMT, ME, PM, FIELD, VIEWER},
        "add": {ME, FIELD, PM},
        "review": {ME, PM},
        "evaluate": {ME},
        "delete": set(),
    },
    "results": {
        "view": {MGMT, ME, PM, VIEWER},
        "add": {ME},
        "edit": {ME},
        "delete": set(),
    },
    "beneficiaries": {
        "view": {MGMT, ME, PM, FIELD, FIN, DATA},
        "add": {DATA, FIELD},
        "edit": {DATA},
        "delete": set(),
    },
    "finance": {
        "view": {MGMT, FIN},
        "add": {FIN},
        "edit": {FIN},
        "delete": set(),
    },
    "grm": {
        "view": {MGMT, ME, PM, GRM},
        "add": {GRM},
        "edit": {GRM},
        "delete": set(),
    },
    "documents": {
        "view": ALL_ROLES,
        "add": {ME, PM, FIELD, DATA, FIN},
        "edit": set(),
        "delete": {PM},
        "restricted": {MGMT, ME, PM, FIN, DATA, GRM},   # may open Restricted docs
    },
    "reports": {
        "view": {MGMT, ME, PM, FIN, GRM, DATA},
        "add": set(),
        "edit": set(),
        "delete": set(),
    },
    "notifications": {"view": ALL_ROLES},
    "users": {"view": set(), "add": set(), "edit": set(), "delete": set()},
    "audit": {"view": set()},
}

# Which report types each role may generate.
REPORT_ACCESS = {
    "project": {MGMT, ME, PM, DATA},
    "progress": {MGMT, ME, PM},
    "district": {MGMT, ME, PM},
    "beneficiary": {MGMT, ME, PM, DATA},
    "me": {MGMT, ME},
    "finance": {MGMT, FIN},
    "grm": {MGMT, GRM, ME, PM},
    "delayed": {MGMT, ME, PM},
    "completed": {MGMT, ME, PM},
    "monthly": {MGMT, ME, PM},
    "quarterly": {MGMT, ME, PM},
    "annual": {MGMT, ME, PM},
}


def role_of(user):
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return ADMIN
    return user.role_name


def is_admin(user):
    return role_of(user) == ADMIN


def can(user, module, action="view"):
    role = role_of(user)
    if role is None:
        return False
    if role == ADMIN:
        return True
    return role in PERMISSIONS.get(module, {}).get(action, set())


def can_report(user, report_type):
    role = role_of(user)
    return role == ADMIN or role in REPORT_ACCESS.get(report_type, set())


def module_required(module, action="view"):
    """View decorator: login required, then role must allow module/action."""
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            if not can(request.user, module, action):
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


def admin_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        if not is_admin(request.user):
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapper


class ModuleRequiredMixin(LoginRequiredMixin):
    module = None
    action = "view"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not can(request.user, self.module, self.action):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
