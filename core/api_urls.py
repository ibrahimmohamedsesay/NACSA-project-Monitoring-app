from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import api

router = DefaultRouter()
router.register("projects", api.ProjectViewSet, basename="api-project")
router.register("progress-updates", api.ProgressUpdateViewSet, basename="api-update")
router.register("indicators", api.IndicatorViewSet, basename="api-indicator")
router.register("grm-cases", api.GRMCaseViewSet, basename="api-grm")
router.register("notifications", api.NotificationViewSet, basename="api-notification")

urlpatterns = [path("", include(router.urls)), path("summary/", api.summary, name="api-summary")]
