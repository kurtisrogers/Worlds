"""Integration URL configuration."""

from django.urls import path

from integrations import views

app_name = "integrations"

urlpatterns = [
    path("google/auth/", views.google_auth_start, name="google_auth_start"),
    path("google/callback/", views.google_auth_callback, name="google_callback"),
    path("<slug:slug>/", views.integrations_manage, name="manage"),
    path("<slug:slug>/google-sheet/", views.connect_google_sheet, name="google_sheet"),
    path("<slug:slug>/google-sheet/sync/", views.sync_google_sheet, name="sync_sheet"),
    path("<slug:slug>/upload/", views.upload_document, name="upload"),
]
