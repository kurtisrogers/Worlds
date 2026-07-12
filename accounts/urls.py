"""Account URL configuration."""

from django.urls import path

from accounts import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.WorldsLoginView.as_view(), name="login"),
    path("logout/", views.WorldsLogoutView.as_view(), name="logout"),
    path("register/", views.register, name="register"),
    path("profile/", views.profile, name="profile"),
]
