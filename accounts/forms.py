from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm, PasswordResetForm

from core.forms import StyledFormMixin, StyledModelForm
from .models import Role

User = get_user_model()


class LoginForm(StyledFormMixin, forms.Form):
    username = forms.CharField(label="Username or email", widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))
    remember_me = forms.BooleanField(required=False)

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        data = super().clean()
        ident, pw = data.get("username"), data.get("password")
        if ident and pw:
            username = ident
            if "@" in ident:
                u = User.objects.filter(email__iexact=ident).first()
                if u:
                    username = u.get_username()
            self.user = authenticate(self.request, username=username, password=pw)
            if self.user is None:
                raise forms.ValidationError("invalid")
            if not self.user.is_active:
                raise forms.ValidationError("inactive")
        return data


class StyledPasswordChange(StyledFormMixin, PasswordChangeForm):
    pass


class StyledSetPassword(StyledFormMixin, SetPasswordForm):
    pass


class StyledPasswordReset(StyledFormMixin, PasswordResetForm):
    def get_users(self, email):
        return (u for u in super().get_users(email) if u.is_active)


class RegistrationForm(StyledFormMixin, forms.Form):
    username = forms.CharField(max_length=150)
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField()
    role = forms.ModelChoiceField(queryset=Role.objects.none(), label="Role")
    password1 = forms.CharField(widget=forms.PasswordInput(render_value=False), label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput(render_value=False), label="Confirm password")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].queryset = Role.objects.order_by("name")

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("A user with that username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with that email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        pw1 = cleaned_data.get("password1")
        pw2 = cleaned_data.get("password2")
        if pw1 and pw2 and pw1 != pw2:
            raise forms.ValidationError("The two password fields did not match.")
        return cleaned_data

    def save(self):
        role = self.cleaned_data["role"]
        user = User.objects.create_user(
            username=self.cleaned_data["username"].strip(),
            email=self.cleaned_data["email"].strip(),
            first_name=self.cleaned_data["first_name"].strip(),
            last_name=self.cleaned_data["last_name"].strip(),
            password=self.cleaned_data["password1"],
            role=role,
        )
        is_admin_role = role.name == Role.ADMINISTRATOR
        user.is_staff = is_admin_role
        user.is_superuser = is_admin_role
        user.save(update_fields=["is_staff", "is_superuser"])
        return user


class ProfileForm(StyledModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone_number", "department"]


class UserForm(StyledModelForm):
    password = forms.CharField(required=False, widget=forms.PasswordInput(render_value=False),
                               help_text="Leave blank to keep the current password when editing.")
    role = forms.ModelChoiceField(queryset=Role.objects.all(), required=True)

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "role", "department", "phone_number", "is_active", "password"]

    def clean_password(self):
        pw = self.cleaned_data.get("password")
        if not self.instance.pk and not pw:
            raise forms.ValidationError("A password is required for a new user.")
        if pw:
            from django.contrib.auth.password_validation import validate_password
            validate_password(pw, self.instance)
        return pw

    def save(self, commit=True):
        user = super().save(commit=False)
        pw = self.cleaned_data.get("password")
        if pw:
            user.set_password(pw)
        if commit:
            user.save()
        return user
