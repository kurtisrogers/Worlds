# Google Sheets Integration

Connect a spreadsheet to automatically sync chapters.

## Sheet format

| Number | Title | Content |
|--------|-------|---------|
| 1 | The Beginning | Chapter text here... |
| 2 | Rising Action | More text... |

## Setup

1. Go to **Manage → Integrations → Connect Google Sheet**
2. Paste the Spreadsheet ID from the URL
3. Set the sheet tab name (default: `Chapters`)
4. Click **Sync now** to import

OAuth credentials (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`) are required for live API sync.
