from django.urls import path
from . import views

app_name = "beneficiaries"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("register/", views.beneficiary_list, name="list"),
    path("new/", views.beneficiary_create, name="create"),
    path("<int:pk>/", views.beneficiary_detail, name="detail"),
    path("<int:pk>/edit/", views.beneficiary_edit, name="edit"),
    path("<int:pk>/link/", views.link_add, name="link_add"),
    path("link/<int:pk>/status/", views.link_status, name="link_status"),
]
