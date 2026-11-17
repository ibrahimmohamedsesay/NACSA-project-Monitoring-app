from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Role, User


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "description")


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "get_full_name", "email", "role", "is_active")
    list_filter = ("role", "is_active", "is_staff")
    fieldsets = UserAdmin.fieldsets + (("NaCSA", {"fields": ("role", "department", "phone_number")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("NaCSA", {"fields": ("role", "department", "phone_number")}),)
