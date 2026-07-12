"""Editor URL configuration."""

from django.urls import path

from editor import views

app_name = "editor"

urlpatterns = [
    path("<slug:slug>/<int:number>/", views.editor, name="edit"),
    path("<slug:slug>/<int:number>/autosave/", views.autosave, name="autosave"),
]
