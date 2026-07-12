from django.contrib import admin

from engagement.models import ChapterComment, ChapterReaction


@admin.register(ChapterComment)
class ChapterCommentAdmin(admin.ModelAdmin):
    list_display = ["user", "chapter", "created_at"]
    search_fields = ["body", "user__username"]


@admin.register(ChapterReaction)
class ChapterReactionAdmin(admin.ModelAdmin):
    list_display = ["user", "chapter", "reaction_type", "created_at"]
    list_filter = ["reaction_type"]
