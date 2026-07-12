"""Library URL configuration."""

from django.urls import path

from library import views

app_name = "library"

urlpatterns = [
    path("", views.library, name="index"),
    path("authors/<str:username>/", views.author_profile, name="author"),
    path("authors/<str:username>/follow/", views.toggle_follow, name="toggle_follow"),
    path("<slug:slug>/save/", views.toggle_save, name="toggle_save"),
]
