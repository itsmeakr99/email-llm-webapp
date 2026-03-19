import base64
import json
from email.message import EmailMessage
from pathlib import Path
from urllib import parse, request as urllib_request, error as urllib_error

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.models import SendEmailRequest
from app.settings import get_settings

GOOGLE_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
TOKEN_FILE_PATH = Path("google_token.txt")


def _load_refresh_token(settings) -> str:
    if settings.google_refresh_token:
        return settings.google_refresh_token.strip()

    if TOKEN_FILE_PATH.exists():
        token = TOKEN_FILE_PATH.read_text(encoding="utf-8").strip()
        if token:
            return token

    return ""


def _save_refresh_token(refresh_token: str) -> None:
    if refresh_token:
        TOKEN_FILE_PATH.write_text(refresh_token.strip(), encoding="utf-8")


def build_google_auth_url() -> str:
    settings = get_settings()

    required = {
        "GOOGLE_CLIENT_ID": settings.google_client_id,
        "GOOGLE_REDIRECT_URI": settings.google_redirect_uri,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise ValueError(f"Missing Google OAuth configuration: {', '.join(missing)}")

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": " ".join(GOOGLE_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
    }

    return f"{GOOGLE_AUTH_URI}?{parse.urlencode(params)}"


def exchange_google_code_for_tokens(code: str) -> dict:
    settings = get_settings()

    required = {
        "GOOGLE_CLIENT_ID": settings.google_client_id,
        "GOOGLE_CLIENT_SECRET": settings.google_client_secret,
        "GOOGLE_REDIRECT_URI": settings.google_redirect_uri,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise ValueError(f"Missing Google OAuth configuration: {', '.join(missing)}")

    payload = parse.urlencode(
        {
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")

    req = urllib_request.Request(
        GOOGLE_TOKEN_URI,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with urllib_request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8")
            token_data = json.loads(body)

    except urllib_error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Google token exchange failed: {body}") from exc

    refresh_token = token_data.get("refresh_token") or _load_refresh_token(settings)
    if not refresh_token:
        raise ValueError(
            "Google did not return a refresh token. Revoke the app in your Google account, "
            "then retry with prompt=consent, or use a fresh OAuth client."
        )

    _save_refresh_token(refresh_token)

    return {
        "message": "Gmail connected successfully.",
        "refresh_token": refresh_token,
        "has_refresh_token": True,
    }


def _get_google_credentials() -> Credentials:
    settings = get_settings()

    required = {
        "GOOGLE_CLIENT_ID": settings.google_client_id,
        "GOOGLE_CLIENT_SECRET": settings.google_client_secret,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise ValueError(f"Missing Google OAuth configuration: {', '.join(missing)}")

    refresh_token = _load_refresh_token(settings)
    if not refresh_token:
        raise ValueError(
            "Missing Google refresh token. Connect Gmail first or set GOOGLE_REFRESH_TOKEN."
        )

    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=GOOGLE_TOKEN_URI,
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=GOOGLE_SCOPES,
    )
    credentials.refresh(Request())
    return credentials


def send_email_via_gmail(request: SendEmailRequest) -> None:
    settings = get_settings()

    if not settings.google_sender_email:
        raise ValueError("Missing Google sender email: GOOGLE_SENDER_EMAIL")

    credentials = _get_google_credentials()

    message = EmailMessage()
    message["From"] = settings.google_sender_email
    message["To"] = ", ".join(request.to)
    if request.cc:
        message["Cc"] = ", ".join(request.cc)
    message["Subject"] = request.subject
    message.set_content(request.body)

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
    service.users().messages().send(
        userId="me",
        body={"raw": raw_message},
    ).execute()
