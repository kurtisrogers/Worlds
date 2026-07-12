"""Google OAuth flow for Sheets API access."""

from __future__ import annotations

import logging

from django.conf import settings
from django.utils import timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from integrations.models import GoogleCredential

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# Allow OAuth over HTTP in development
if settings.DEBUG:
    import os

    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"


def _client_config() -> dict:
    return {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
        }
    }


def create_oauth_flow(state: str | None = None) -> Flow:
    flow = Flow.from_client_config(
        _client_config(),
        scopes=SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
    )
    if state:
        flow.state = state
    return flow


def get_authorization_url(state: str) -> str:
    flow = create_oauth_flow(state=state)
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url


def exchange_code_for_credentials(code: str) -> Credentials:
    flow = create_oauth_flow()
    flow.fetch_token(code=code)
    return flow.credentials


def save_credentials(user, creds: Credentials) -> GoogleCredential:
    expiry = creds.expiry
    if expiry and timezone.is_naive(expiry):
        expiry = timezone.make_aware(expiry)

    credential, _ = GoogleCredential.objects.update_or_create(
        user=user,
        defaults={
            "access_token": creds.token,
            "refresh_token": creds.refresh_token or "",
            "token_expiry": expiry,
            "scopes": " ".join(creds.scopes or SCOPES),
        },
    )
    return credential


def get_credentials(user) -> Credentials | None:
    """Return valid Google credentials for a user, refreshing if needed."""
    try:
        stored = user.google_credential
    except GoogleCredential.DoesNotExist:
        return None

    creds = Credentials(
        token=stored.access_token,
        refresh_token=stored.refresh_token or None,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=stored.scopes.split() if stored.scopes else SCOPES,
    )
    if stored.token_expiry:
        creds.expiry = stored.token_expiry

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            save_credentials(user, creds)
        except Exception:
            logger.exception("Failed to refresh Google token for user %s", user.pk)
            return None

    return creds


def user_has_google_credentials(user) -> bool:
    return GoogleCredential.objects.filter(user=user).exists()
