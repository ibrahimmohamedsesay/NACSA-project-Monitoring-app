from django.urls import path
from . import views

app_name = "monitoring"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("updates/", views.update_list, name="update_list"),
    path("updates/<int:pk>/review/", views.update_review, name="update_review"),
    path("project/<int:pk>/update/", views.update_create, name="update_create"),
    path("project/<int:pk>/visit/", views.visit_create, name="visit_create"),
    path("project/<int:pk>/evaluation/", views.evaluation_create, name="evaluation_create"),
]
