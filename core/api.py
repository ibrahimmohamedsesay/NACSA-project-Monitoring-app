"""Read-only REST API (session authentication) that obeys the same role matrix as the web UI."""
from django.db.models import Count
from rest_framework import permissions, serializers, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from core.permissions import can
from grm.models import GRMCase
from monitoring.models import ProgressUpdate
from notifications.models import Notification
from projects.models import Project
from results.models import ResultIndicator


class ModulePermission(permissions.BasePermission):
    module = None

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and can(request.user, view.module, "view"))


class ProjectSer(serializers.ModelSerializer):
    health = serializers.CharField(read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Project
        fields = ["id", "project_id", "name", "project_type", "district", "chiefdom", "community", "status", "status_label", "health",
                  "completion_percentage", "budget", "start_date", "expected_completion_date", "target_beneficiaries"]


class UpdateSer(serializers.ModelSerializer):
    class Meta:
        model = ProgressUpdate
        fields = ["id", "project", "date", "progress_percentage", "review_status", "challenges"]


class IndicatorSer(serializers.ModelSerializer):
    achievement_percentage = serializers.FloatField(read_only=True)

    class Meta:
        model = ResultIndicator
        fields = ["id", "project", "name", "indicator_type", "baseline", "target", "current_value", "status", "achievement_percentage"]


class GRMSer(serializers.ModelSerializer):
    class Meta:
        model = GRMCase
        fields = ["id", "case_id", "project", "category", "status", "created_at"]


class NotifSer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "event_type", "message", "is_read", "link", "created_at"]


class ProjectViewSet(viewsets.ReadOnlyModelViewSet):
    module = "projects"
    permission_classes = [ModulePermission]
    serializer_class = ProjectSer
    filterset_fields = None

    def get_queryset(self):
        qs = Project.objects.filter(is_archived=False)
        for k in ("status", "district", "project_type"):
            if self.request.query_params.get(k):
                qs = qs.filter(**{k: self.request.query_params[k]})
        return qs


class ProgressUpdateViewSet(viewsets.ReadOnlyModelViewSet):
    module = "monitoring"
    permission_classes = [ModulePermission]
    serializer_class = UpdateSer
    queryset = ProgressUpdate.objects.all()


class IndicatorViewSet(viewsets.ReadOnlyModelViewSet):
    module = "results"
    permission_classes = [ModulePermission]
    serializer_class = IndicatorSer
    queryset = ResultIndicator.objects.all()


class GRMCaseViewSet(viewsets.ReadOnlyModelViewSet):
    module = "grm"
    permission_classes = [ModulePermission]
    serializer_class = GRMSer
    queryset = GRMCase.objects.all()


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    module = "notifications"
    permission_classes = [ModulePermission]
    serializer_class = NotifSer

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def summary(request):
    ps = Project.objects.filter(is_archived=False)
    return Response({"projects": ps.count(), "by_status": {r["status"]: r["n"] for r in ps.values("status").annotate(n=Count("id"))}})
