from django.contrib import admin

from library.models import AuthorFollow, SavedStory


@admin.register(SavedStory)
class SavedStoryAdmin(admin.ModelAdmin):
    list_display = ["user", "story", "saved_at"]
    list_filter = ["saved_at"]


@admin.register(AuthorFollow)
class AuthorFollowAdmin(admin.ModelAdmin):
    list_display = ["follower", "author", "followed_at"]
