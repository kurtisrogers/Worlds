# Google OAuth

Full OAuth flow for Google Sheets sync.

## Flow

1. Author clicks **Connect Google account** on the integrations page
2. Redirected to Google consent screen (spreadsheets.readonly scope)
3. Callback stores tokens in `GoogleCredential` model
4. Tokens auto-refresh when expired

## Configuration

Set in `.env`:

```
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/integrations/google/callback/
```

Register the redirect URI in Google Cloud Console under OAuth 2.0 credentials.

## Syncing

After connecting Google and configuring a spreadsheet ID, click **Sync now** to import chapters.
