"""Integration views for Google Sheets and document uploads."""

import secrets

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from integrations.documents import process_document_upload
from integrations.google_oauth import (
    exchange_code_for_credentials,
    get_authorization_url,
    save_credentials,
    user_has_google_credentials,
)
from integrations.models import DocumentUpload, GoogleSheetConnection
from integrations.sheets import sync_from_google_sheets
from stories.models import ContentSource, Story


@login_required
def google_auth_start(request):
    """Redirect user to Google OAuth consent screen."""
    state = secrets.token_urlsafe(32)
    request.session["google_oauth_state"] = state
    request.session["google_oauth_next"] = request.GET.get(
        "next", request.META.get("HTTP_REFERER", "/")
    )
    return redirect(get_authorization_url(state))


@login_required
def google_auth_callback(request):
    """Handle Google OAuth callback and store credentials."""
    state = request.session.pop("google_oauth_state", None)
    next_url = request.session.pop("google_oauth_next", "/")

    if request.GET.get("state") != state:
        messages.error(request, "Invalid OAuth state. Please try again.")
        return redirect(next_url)

    error = request.GET.get("error")
    if error:
        messages.error(request, f"Google authorization failed: {error}")
        return redirect(next_url)

    code = request.GET.get("code")
    if not code:
        messages.error(request, "No authorization code received.")
        return redirect(next_url)

    try:
        creds = exchange_code_for_credentials(code)
        save_credentials(request.user, creds)
        messages.success(request, "Google account connected successfully.")
    except Exception:
        messages.error(
            request, "Failed to connect Google account. Check your OAuth settings."
        )

    return redirect(next_url)


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
        {
            "story": story,
            "connection": connection,
            "google_connected": user_has_google_credentials(request.user),
        },
    )


@login_required
def sync_google_sheet(request, slug):
    story = get_object_or_404(Story, slug=slug, author=request.user)
    connection = get_object_or_404(GoogleSheetConnection, story=story)

    if not user_has_google_credentials(request.user):
        messages.warning(request, "Connect your Google account first.")
        return redirect(
            f"{reverse('integrations:google_auth_start')}?next={request.path}"
        )

    count = sync_from_google_sheets(connection)
    if count:
        messages.success(request, f"Synced {count} chapters from Google Sheets.")
    else:
        messages.warning(
            request,
            "No chapters synced. Check your sheet format and spreadsheet ID.",
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
        {
            "story": story,
            "connection": connection,
            "uploads": uploads,
            "google_connected": user_has_google_credentials(request.user),
        },
    )
