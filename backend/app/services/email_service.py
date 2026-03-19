import base64
import json
from email.message import EmailMessage
from urllib import error as urllib_error
from urllib import parse
from urllib import request as urllib_request

from google.auth.transport.requests import Request
from google.oauth2 import id_token as google_id_token
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.models import SendEmailRequest
from app.services.user_service import (
    create_google_state,
    get_current_app_user,
    get_gmail_account,
    read_google_state,
    save_gmail_account,
)
from app.settings import get_settings

GOOGLE_SCOPES = [
    "openid",
    "email",
    "https://www.googleapis.com/auth/gmail.send",
]
GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"


def build_google_auth_url_for_user(authorization: str | None) -> str:
    settings = get_settings()
    user = get_current_app_user(authorization)

    required = {
        "GOOGLE_CLIENT_ID": settings.google_client_id,
        "GOOGLE_REDIRECT_URI": settings.google_redirect_uri,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise ValueError(f"Missing Google OAuth configuration: {', '.join(missing)}")

    state = create_google_state(user["id"])

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": " ".join(GOOGLE_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }

    return f"{GOOGLE_AUTH_URI}?{parse.urlencode(params)}"


def exchange_google_code_for_tokens(code: str, state: str) -> dict[str, str]:
    settings = get_settings()

    required = {
        "GOOGLE_CLIENT_ID": settings.google_client_id,
        "GOOGLE_CLIENT_SECRET": settings.google_client_secret,
        "GOOGLE_REDIRECT_URI": settings.google_redirect_uri,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise ValueError(f"Missing Google OAuth configuration: {', '.join(missing)}")

    user_id = read_google_state(state)

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

    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        raise ValueError(
            "Google did not return a refresh token. Remove this app from your Google account and connect again."
        )

    raw_id_token = token_data.get("id_token")
    if not raw_id_token:
        raise ValueError("Google did not return an ID token.")

    token_info = google_id_token.verify_oauth2_token(
        raw_id_token,
        Request(),
        settings.google_client_id,
    )

    gmail_email = token_info.get("email")
    if not gmail_email:
        raise ValueError("Google did not return the Gmail address.")

    save_gmail_account(user_id, gmail_email, refresh_token)

    return {
        "message": "Gmail connected successfully.",
        "gmail_email": gmail_email,
    }


def get_gmail_connection_status_for_user(authorization: str | None) -> dict[str, str | bool | None]:
    user = get_current_app_user(authorization)
    account = get_gmail_account(user["id"])

    if not account:
        return {
            "connected": False,
            "gmail_email": None,
        }

    return {
        "connected": True,
        "gmail_email": account["gmail_email"],
    }


def _get_google_credentials_for_user(authorization: str | None) -> tuple[Credentials, str]:
    settings = get_settings()
    user = get_current_app_user(authorization)
    account = get_gmail_account(user["id"])

    if not account:
        raise ValueError("No Gmail account connected. Click Connect Gmail first.")

    credentials = Credentials(
        token=None,
        refresh_token=account["google_refresh_token"],
        token_uri=GOOGLE_TOKEN_URI,
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=GOOGLE_SCOPES,
    )
    credentials.refresh(Request())

    return credentials, account["gmail_email"]


def send_email_via_gmail_for_user(request: SendEmailRequest, authorization: str | None) -> None:
    credentials, sender_email = _get_google_credentials_for_user(authorization)

    message = EmailMessage()
    message["From"] = sender_email
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
