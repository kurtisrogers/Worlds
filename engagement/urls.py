"""Engagement URL configuration."""

from django.urls import path

from engagement import views

app_name = "engagement"

urlpatterns = [
    path(
        "<slug:slug>/chapters/<int:number>/comments/",
        views.post_comment,
        name="post_comment",
    ),
    path(
        "<slug:slug>/chapters/<int:number>/react/",
        views.toggle_reaction,
        name="toggle_reaction",
    ),
]
