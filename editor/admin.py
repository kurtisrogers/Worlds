from django.contrib import admin

from editor.models import AICall, ReviewFinding


@admin.register(AICall)
class AICallAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "user",
        "story",
        "chapter",
        "model",
        "provider",
        "outcome",
        "cost_cents",
    )
    list_filter = ("outcome", "provider")
    readonly_fields = (
        "user",
        "story",
        "chapter",
        "model",
        "provider",
        "created_at",
        "outcome",
        "sent_to_provider",
        "input_tokens",
        "output_tokens",
        "cost_cents",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ReviewFinding)
class ReviewFindingAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "chapter",
        "asked_by",
        "kind",
        "status",
        "model",
    )
    list_filter = ("kind", "status")
    readonly_fields = (
        "chapter",
        "asked_by",
        "anchor",
        "question",
        "status",
        "model",
        "kind",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
