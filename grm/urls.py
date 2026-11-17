from django.urls import path
from . import views

app_name = "grm"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("cases/", views.case_list, name="list"),
    path("cases/new/", views.case_create, name="create"),
    path("cases/<int:pk>/", views.case_detail, name="detail"),
]
