"""Integration views for Google Sheets and document uploads."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from integrations.documents import process_document_upload
from integrations.models import DocumentUpload, GoogleSheetConnection
from integrations.sheets import sync_from_google_sheets
from stories.models import ContentSource, Story


@login_required
def connect_google_sheet(request, slug):
    story = get_object_or_404(Story, slug=slug, author=request.user)

    if request.method == "POST":
        spreadsheet_id = request.POST.get("spreadsheet_id", "").strip()
        sheet_name = request.POST.get("sheet_name", "Chapters").strip()
        if spreadsheet_id:
            GoogleSheetConnection.objects.update_or_create(
                story=story,
                defaults={
                    "spreadsheet_id": spreadsheet_id,
                    "sheet_name": sheet_name,
                },
            )
            story.content_source = ContentSource.SHEETS
            story.save(update_fields=["content_source"])
            messages.success(request, "Google Sheet connected.")
        return redirect("integrations:manage", slug=slug)

    connection = getattr(story, "google_sheet", None)
    return render(
        request,
        "integrations/google_sheet.html",
        {"story": story, "connection": connection},
    )


@login_required
def sync_google_sheet(request, slug):
    story = get_object_or_404(Story, slug=slug, author=request.user)
    connection = get_object_or_404(GoogleSheetConnection, story=story)
    count = sync_from_google_sheets(connection)
    if count:
        messages.success(request, f"Synced {count} chapters from Google Sheets.")
    else:
        messages.warning(
            request,
            "No chapters synced. Check your sheet format and Google credentials.",
        )
    return redirect("integrations:manage", slug=slug)


@login_required
def upload_document(request, slug):
    story = get_object_or_404(Story, slug=slug, author=request.user)

    if request.method == "POST" and request.FILES.get("document"):
        uploaded_file = request.FILES["document"]
        upload = DocumentUpload.objects.create(
            story=story,
            file=uploaded_file,
            original_filename=uploaded_file.name,
        )
        count = process_document_upload(upload)
        if count:
            story.content_source = ContentSource.UPLOAD
            story.save(update_fields=["content_source"])
            messages.success(
                request, f"Imported {count} chapters from {uploaded_file.name}."
            )
        else:
            messages.error(request, "Failed to parse document. Check the file format.")
        return redirect("integrations:manage", slug=slug)

    uploads = story.document_uploads.all()[:10]
    return render(
        request,
        "integrations/upload.html",
        {"story": story, "uploads": uploads},
    )


@login_required
def integrations_manage(request, slug):
    story = get_object_or_404(Story, slug=slug, author=request.user)
    connection = getattr(story, "google_sheet", None)
    uploads = story.document_uploads.all()[:5]
    return render(
        request,
        "integrations/manage.html",
        {"story": story, "connection": connection, "uploads": uploads},
    )
