import base64
from email.message import EmailMessage
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.models import SendEmailRequest
from app.settings import get_settings

GOOGLE_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
TOKEN_FILE_PATH = Path("google_token.txt")


def _client_config(settings) -> dict:
    return {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": GOOGLE_TOKEN_URI,
        }
    }


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
        "GOOGLE_CLIENT_SECRET": settings.google_client_secret,
        "GOOGLE_REDIRECT_URI": settings.google_redirect_uri,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise ValueError(f"Missing Google OAuth configuration: {', '.join(missing)}")

    flow = Flow.from_client_config(
        _client_config(settings),
        scopes=GOOGLE_SCOPES,
        redirect_uri=settings.google_redirect_uri,
    )

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )
    return auth_url


def exchange_google_code_for_tokens(code: str) -> dict:
    settings = get_settings()

    flow = Flow.from_client_config(
        _client_config(settings),
        scopes=GOOGLE_SCOPES,
        redirect_uri=settings.google_redirect_uri,
    )

    flow.fetch_token(code=code)
    credentials = flow.credentials

    refresh_token = credentials.refresh_token or _load_refresh_token(settings)
    if not refresh_token:
        raise ValueError(
            "Google did not return a refresh token. Reconnect Gmail and make sure consent is granted."
        )

    _save_refresh_token(refresh_token)

    return {
        "refresh_token_saved": True,
        "has_refresh_token": bool(refresh_token),
        "message": (
            "Gmail connected successfully. "
            "For permanent storage on Render, copy this refresh token into GOOGLE_REFRESH_TOKEN."
        ),
        "refresh_token": refresh_token,
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
    if request.bcc:
        message["Bcc"] = ", ".join(request.bcc)
    message["Subject"] = request.subject
    message.set_content(request.body)

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
    service.users().messages().send(
        userId="me",
        body={"raw": raw_message},
    ).execute()
