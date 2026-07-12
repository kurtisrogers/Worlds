"""Staff URL configuration."""

from django.urls import path

from accounts import staff_views

app_name = "staff"

urlpatterns = [
    path("", staff_views.staff_dashboard, name="dashboard"),
    path("users/", staff_views.staff_users, name="users"),
    path("users/<str:username>/", staff_views.staff_user_detail, name="user_detail"),
    path("users/<str:username>/role/", staff_views.staff_set_role, name="set_role"),
    path("comments/", staff_views.staff_comments, name="comments"),
    path(
        "comments/<int:comment_id>/delete/",
        staff_views.staff_delete_comment,
        name="delete_comment",
    ),
]
