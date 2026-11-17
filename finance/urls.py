from django.urls import path
from . import views

app_name = "finance"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("payments/", views.payment_list, name="list"),
    path("payments/new/", views.payment_create, name="create"),
    path("payments/<int:pk>/edit/", views.payment_edit, name="edit"),
]
