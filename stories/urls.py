"""Story URL configuration."""

from django.urls import path

from stories import counts, views

app_name = "stories"

urlpatterns = [
    path("", views.home, name="home"),
    path("discover/", views.discover, name="discover"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("new/", views.story_create, name="create"),
    path("<slug:slug>/", views.story_detail, name="detail"),
    path("<slug:slug>/manage/", views.story_manage, name="manage"),
    path("<slug:slug>/edit/", views.story_edit, name="edit"),
    path("<slug:slug>/chapters/new/", views.chapter_create, name="chapter_create"),
    path(
        "<slug:slug>/chapters/<int:number>/",
        views.chapter_read,
        name="chapter",
    ),
    path("<slug:slug>/counts/", counts.chapter_counts, name="chapter_counts"),
    path(
        "<slug:slug>/chapters/<int:number>/reads/",
        counts.record_read,
        name="record_read",
    ),
    path(
        "<slug:slug>/chapters/<int:number>/likes/",
        counts.chapter_like,
        name="chapter_like",
    ),
    path(
        "<slug:slug>/chapters/<int:number>/favourites/",
        counts.chapter_favourite,
        name="chapter_favourite",
    ),
    path(
        "<slug:slug>/chapters/<int:number>/edit/",
        views.chapter_edit,
        name="chapter_edit",
    ),
    path(
        "<slug:slug>/chapters/<int:number>/unlock/",
        views.unlock_chapter,
        name="unlock_chapter",
    ),
    path(
        "<slug:slug>/subscribe/<str:tier_name>/",
        views.subscribe_tier,
        name="subscribe_tier",
    ),
]
