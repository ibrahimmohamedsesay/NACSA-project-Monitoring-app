from django.contrib import admin
from .models import Project, ProjectActivity, ProjectMilestone, ProjectApproval


class ActivityInline(admin.TabularInline):
    model = ProjectActivity
    extra = 0


class MilestoneInline(admin.TabularInline):
    model = ProjectMilestone
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("project_id", "name", "district", "status", "completion_percentage", "budget", "is_archived")
    list_filter = ("status", "district", "project_type", "is_archived")
    search_fields = ("project_id", "name", "community")
    inlines = [ActivityInline, MilestoneInline]


admin.site.register(ProjectApproval)
