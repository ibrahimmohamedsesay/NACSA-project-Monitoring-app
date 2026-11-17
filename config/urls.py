"""Root URL configuration for the NaCSA Community Project Management & Monitoring System."""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

handler403 = "core.views.permission_denied"
handler404 = "core.views.not_found"
handler500 = "core.views.server_error"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("dashboard.urls")),
    path("accounts/", include("accounts.urls")),
    path("projects/", include("projects.urls")),
    path("monitoring/", include("monitoring.urls")),
    path("results/", include("results.urls")),
    path("beneficiaries/", include("beneficiaries.urls")),
    path("finance/", include("finance.urls")),
    path("grm/", include("grm.urls")),
    path("documents/", include("documents.urls")),
    path("reports/", include("reports.urls")),
    path("notifications/", include("notifications.urls")),
    path("audit/", include("audit.urls")),
    path("api/", include("core.api_urls")),
]

if settings.DEBUG:
    # Only evidence photos are served directly; documents go through the access-controlled download view.
    urlpatterns += [re_path(r"^media/(?P<path>evidence/.*)$", serve, {"document_root": settings.MEDIA_ROOT})]
