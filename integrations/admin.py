from django.contrib import admin

from integrations.models import DocumentUpload, GoogleCredential, GoogleSheetConnection


@admin.register(GoogleCredential)
class GoogleCredentialAdmin(admin.ModelAdmin):
    list_display = ["user", "token_expiry", "updated_at"]
    readonly_fields = ["access_token", "refresh_token"]


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
