from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (PasswordResetView, PasswordResetDoneView,
                                       PasswordResetConfirmView, PasswordResetCompleteView)
from django.core.cache import cache
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from audit.utils import log
from core.permissions import admin_required
from core.utils import client_ip, paginate
from .forms import (LoginForm, ProfileForm, RegistrationForm, StyledPasswordChange,
                    StyledPasswordReset, StyledSetPassword, UserForm)
from .models import Role, User


def _lock_key(request, ident):
    return f"login-fail:{client_ip(request)}:{(ident or '').lower()}"


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:index")

    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        log(user, "create", "accounts", user.pk, f"User account created for {user.username} ({user.role})")
        messages.success(request, "Your account has been created. You can sign in now.")
        return redirect("accounts:login")

    return render(request, "accounts/register.html", {"form": form, "page_title": "Create account"})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:index")
    nxt = request.POST.get("next") or request.GET.get("next", "")
    ident = request.POST.get("username", "")
    locked = False
    form = LoginForm(request, request.POST or None)
    if request.method == "POST":
        key = _lock_key(request, ident)
        if cache.get(key, 0) >= settings.LOGIN_MAX_ATTEMPTS:
            locked = True
            form = LoginForm(request)
        elif form.is_valid():
            cache.delete(key)
            login(request, form.user)
            request.session.set_expiry(60 * 60 * 24 * 14 if form.cleaned_data["remember_me"] else 0)
            log(form.user, "login", "accounts", form.user.pk, "User signed in")
            if nxt and url_has_allowed_host_and_scheme(nxt, {request.get_host()}):
                return redirect(nxt)
            return redirect("dashboard:index")
        else:
            cache.set(key, cache.get(key, 0) + 1, settings.LOGIN_LOCKOUT_MINUTES * 60)
            log(None, "login_failed", "accounts", None, f"Failed sign-in for '{ident[:50]}' from {client_ip(request)}")
    return render(request, "accounts/login.html", {"form": form, "next": nxt, "locked": locked})


@require_POST
def logout_view(request):
    if request.user.is_authenticated:
        log(request.user, "logout", "accounts", request.user.pk, "User signed out")
    logout(request)
    messages.info(request, "You have been signed out.")
    return redirect("accounts:login")


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        log(request.user, "update", "accounts", request.user.pk, "Updated own profile")
        messages.success(request, "Profile updated.")
        return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {"form": form, "page_title": "My profile"})


@login_required
def password_change(request):
    form = StyledPasswordChange(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        log(user, "password_change", "accounts", user.pk, "Changed own password")
        messages.success(request, "Your password was changed.")
        return redirect("accounts:profile")
    return render(request, "generic_form.html", {"form": form, "page_title": "Change password", "submit_label": "Change password", "cancel_url": reverse("accounts:profile")})


class ResetView(PasswordResetView):
    form_class = StyledPasswordReset
    template_name = "accounts/simple_form.html"
    email_template_name = "accounts/password_reset_email.txt"
    success_url = reverse_lazy("accounts:password_reset_done")
    extra_context = {"page_title": "Reset your password", "intro": "Enter the email address on your account and we will send reset instructions.", "submit_label": "Send reset link"}


class ResetDone(PasswordResetDoneView):
    template_name = "accounts/simple_form.html"
    extra_context = {"page_title": "Check your email", "intro": "If an account matches that address, a reset link has been sent. In this prototype the link is printed in the server console."}


class ResetConfirm(PasswordResetConfirmView):
    form_class = StyledSetPassword
    template_name = "accounts/simple_form.html"
    success_url = reverse_lazy("accounts:password_reset_complete")
    extra_context = {"page_title": "Choose a new password", "intro": "Pick a strong password you have not used before.", "submit_label": "Set password"}


class ResetComplete(PasswordResetCompleteView):
    template_name = "accounts/simple_form.html"
    extra_context = {"page_title": "Password updated", "intro": "Your password has been changed. You can now sign in."}


# ---- administrator-only user management ----------------------------------

@admin_required
def user_list(request):
    qs = User.objects.select_related("role")
    q = request.GET.get("q", "").strip()
    role = request.GET.get("role", "")
    status = request.GET.get("status", "")
    if q:
        from django.db.models import Q
        qs = qs.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q))
    if role:
        qs = qs.filter(role__name=role)
    if status in ("active", "inactive"):
        qs = qs.filter(is_active=(status == "active"))
    page, params = paginate(request, qs)
    return render(request, "accounts/user_list.html", {"page": page, "params": params, "roles": Role.objects.all(), "page_title": "User management", "q": q, "sel_role": role, "sel_status": status})


@admin_required
def user_create(request):
    form = UserForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        u = form.save()
        log(request.user, "create", "accounts", u.pk, f"Created user {u.username} ({u.role})")
        messages.success(request, f"User {u.username} created.")
        return redirect("accounts:user_list")
    return render(request, "generic_form.html", {"form": form, "page_title": "Add user", "cancel_url": reverse("accounts:user_list")})


@admin_required
def user_edit(request, pk):
    u = get_object_or_404(User, pk=pk)
    form = UserForm(request.POST or None, instance=u)
    if request.method == "POST" and form.is_valid():
        form.save()
        log(request.user, "update", "accounts", u.pk, f"Updated user {u.username}")
        messages.success(request, "User updated.")
        return redirect("accounts:user_list")
    return render(request, "generic_form.html", {"form": form, "page_title": f"Edit {u.username}", "cancel_url": reverse("accounts:user_list")})


@admin_required
@require_POST
def user_toggle(request, pk):
    u = get_object_or_404(User, pk=pk)
    if u == request.user:
        messages.error(request, "You cannot deactivate your own account.")
    else:
        u.is_active = not u.is_active
        u.save(update_fields=["is_active"])
        log(request.user, "update", "accounts", u.pk, f"{'Activated' if u.is_active else 'Deactivated'} user {u.username}")
        messages.success(request, f"{u.username} is now {'active' if u.is_active else 'inactive'}.")
    return redirect("accounts:user_list")
