from django.contrib import admin

from integrations.models import DocumentUpload, GoogleSheetConnection


@admin.register(GoogleSheetConnection)
class GoogleSheetConnectionAdmin(admin.ModelAdmin):
    list_display = ["story", "spreadsheet_id", "last_synced_at", "sync_enabled"]


@admin.register(DocumentUpload)
class DocumentUploadAdmin(admin.ModelAdmin):
    list_display = [
        "original_filename",
        "story",
        "status",
        "chapters_created",
        "uploaded_at",
    ]
    list_filter = ["status"]
