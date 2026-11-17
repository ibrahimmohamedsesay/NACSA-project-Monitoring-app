from django.urls import path
from . import views

app_name = "reports"
urlpatterns = [
    path("", views.index, name="index"),
    path("data-quality/", views.quality, name="quality"),
    path("<str:kind>/", views.run, name="run"),
]
