from django.contrib import admin
from .models import MonitoringVisit, ProgressUpdate, ProjectEvaluation

admin.site.register(MonitoringVisit)
admin.site.register(ProgressUpdate)
admin.site.register(ProjectEvaluation)
