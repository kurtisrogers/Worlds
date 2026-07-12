"""Google Sheets and document upload models."""

from django.db import models

from stories.models import Story


class GoogleSheetConnection(models.Model):
    """Connection between a story and a Google Spreadsheet."""

    story = models.OneToOneField(
        Story,
        on_delete=models.CASCADE,
        related_name="google_sheet",
    )
    spreadsheet_id = models.CharField(max_length=255)
    sheet_name = models.CharField(max_length=255, default="Chapters")
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    token_expiry = models.DateTimeField(null=True, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    sync_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.story.title} → {self.spreadsheet_id}"


class DocumentUpload(models.Model):
    """Uploaded document file for a story."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PARSED = "parsed", "Parsed"
        FAILED = "failed", "Failed"

    story = models.ForeignKey(
        Story,
        on_delete=models.CASCADE,
        related_name="document_uploads",
    )
    file = models.FileField(upload_to="uploads/")
    original_filename = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    chapters_created = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    parsed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self) -> str:
        return f"{self.original_filename} ({self.story.title})"
