from django.urls import path
from . import views

app_name = "accounts"
urlpatterns = [
    path("register/", views.register_view, name="register"),
    path("signup/", views.register_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile, name="profile"),
    path("password/change/", views.password_change, name="password_change"),
    path("password/reset/", views.ResetView.as_view(), name="password_reset"),
    path("password/reset/sent/", views.ResetDone.as_view(), name="password_reset_done"),
    path("password/reset/<uidb64>/<token>/", views.ResetConfirm.as_view(), name="password_reset_confirm"),
    path("password/reset/complete/", views.ResetComplete.as_view(), name="password_reset_complete"),
    path("users/", views.user_list, name="user_list"),
    path("users/new/", views.user_create, name="user_create"),
    path("users/<int:pk>/edit/", views.user_edit, name="user_edit"),
    path("users/<int:pk>/toggle/", views.user_toggle, name="user_toggle"),
]
