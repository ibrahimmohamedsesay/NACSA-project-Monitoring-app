from django.urls import path
from . import views

app_name = "projects"
urlpatterns = [
    path("", views.project_list, name="list"),
    path("new/", views.project_create, name="create"),
    path("<int:pk>/", views.project_detail, name="detail"),
    path("<int:pk>/edit/", views.project_edit, name="edit"),
    path("<int:pk>/submit/", views.project_submit, name="submit"),
    path("<int:pk>/review/", views.project_review, name="review"),
    path("<int:pk>/status/<str:action>/", views.project_status, name="status"),
    path("<int:pk>/archive/", views.project_archive, name="archive"),
    path("<int:pk>/activities/add/", views.activity_add, name="activity_add"),
    path("<int:pk>/activities/<int:aid>/status/", views.activity_status, name="activity_status"),
    path("<int:pk>/milestones/add/", views.milestone_add, name="milestone_add"),
    path("<int:pk>/milestones/<int:mid>/status/", views.milestone_status, name="milestone_status"),
]
