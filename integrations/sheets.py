"""Google Sheets sync service."""

from __future__ import annotations

import logging
import re
from datetime import datetime

from django.utils import timezone

from integrations.models import GoogleSheetConnection
from stories.models import Chapter

logger = logging.getLogger(__name__)

CHAPTER_HEADER_PATTERN = re.compile(r"^chapter\s+(\d+)", re.IGNORECASE)


def parse_sheet_rows(rows: list[list[str]]) -> list[dict]:
    """
    Parse spreadsheet rows into chapter dicts.

    Expected columns: number, title, content (optional header row).
    """
    if not rows:
        return []

    start = 0
    if rows[0] and rows[0][0].lower() in ("number", "#", "chapter"):
        start = 1

    chapters = []
    for row in rows[start:]:
        if not row or not any(cell.strip() for cell in row):
            continue
        try:
            number = int(row[0].strip().lstrip("#"))
        except (ValueError, IndexError):
            continue
        title = row[1].strip() if len(row) > 1 else f"Chapter {number}"
        content = row[2].strip() if len(row) > 2 else ""
        chapters.append({"number": number, "title": title, "content": content})
    return chapters


def sync_chapters_from_rows(story, chapters_data: list[dict]) -> int:
    """Upsert chapters from parsed data. Returns count of chapters synced."""
    synced = 0
    for data in chapters_data:
        chapter, _ = Chapter.objects.update_or_create(
            story=story,
            number=data["number"],
            defaults={
                "title": data["title"],
                "content": data["content"],
            },
        )
        synced += 1
    return synced


def sync_from_google_sheets(connection: GoogleSheetConnection) -> int:
    """
    Sync chapters from a connected Google Sheet.

    Uses the Google Sheets API when credentials are available;
    falls back to no-op in development without credentials.
    """
    if not connection.access_token:
        logger.warning("No access token for sheet connection %s", connection.pk)
        return 0

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials(token=connection.access_token)
        service = build("sheets", "v4", credentials=creds)
        result = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=connection.spreadsheet_id,
                range=f"{connection.sheet_name}!A:C",
            )
            .execute()
        )
        rows = result.get("values", [])
        chapters_data = parse_sheet_rows(rows)
        count = sync_chapters_from_rows(connection.story, chapters_data)
        connection.last_synced_at = timezone.now()
        connection.save(update_fields=["last_synced_at"])
        return count
    except Exception:
        logger.exception("Google Sheets sync failed for %s", connection.pk)
        return 0
