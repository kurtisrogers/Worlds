"""Integration URL configuration."""

from django.urls import path

from integrations import views

app_name = "integrations"

urlpatterns = [
    path("<slug:slug>/", views.integrations_manage, name="manage"),
    path("<slug:slug>/google-sheet/", views.connect_google_sheet, name="google_sheet"),
    path("<slug:slug>/google-sheet/sync/", views.sync_google_sheet, name="sync_sheet"),
    path("<slug:slug>/upload/", views.upload_document, name="upload"),
]
