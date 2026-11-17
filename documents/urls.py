from django.urls import path
from . import views

app_name = "documents"
urlpatterns = [
    path("", views.document_list, name="list"),
    path("upload/", views.document_upload, name="upload"),
    path("evidence/new/", views.evidence_upload, name="evidence_upload"),
    path("<int:pk>/download/", views.document_download, name="download"),
    path("<int:pk>/delete/", views.document_delete, name="delete"),
]
