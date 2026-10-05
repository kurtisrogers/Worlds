"""Editor URL configuration."""

from django.urls import path

from editor import views

app_name = "editor"

urlpatterns = [
    path("<slug:slug>/<int:number>/", views.editor, name="edit"),
    path("<slug:slug>/<int:number>/autosave/", views.autosave, name="autosave"),
    path("<slug:slug>/<int:number>/assist/", views.assist, name="assist"),
    path("<slug:slug>/<int:number>/review/", views.review, name="review"),
    path("<slug:slug>/<int:number>/findings/", views.findings, name="findings"),
    path(
        "<slug:slug>/<int:number>/findings/<int:finding_id>/dismiss/",
        views.dismiss_finding,
        name="dismiss",
    ),
]
