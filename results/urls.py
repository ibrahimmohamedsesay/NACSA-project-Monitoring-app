from django.urls import path
from . import views

app_name = "results"
urlpatterns = [
    path("", views.indicator_list, name="list"),
    path("new/", views.indicator_create, name="create"),
    path("<int:pk>/edit/", views.indicator_edit, name="edit"),
]
