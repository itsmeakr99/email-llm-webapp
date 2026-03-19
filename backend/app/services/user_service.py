import base64
import hashlib
import hmac
import json
import time

from supabase import Client, create_client

from app.settings import get_settings


def _create_supabase_client() -> Client:
    settings = get_settings()

    required = {
        "SUPABASE_URL": settings.supabase_url,
        "SUPABASE_SERVICE_ROLE_KEY": settings.supabase_service_role_key,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise ValueError(f"Missing Supabase configuration: {', '.join(missing)}")

    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise ValueError("Missing Authorization header.")

    prefix = "bearer "
    if not authorization.lower().startswith(prefix):
        raise ValueError("Authorization header must use Bearer token format.")

    token = authorization[len(prefix):].strip()
    if not token:
        raise ValueError("Missing bearer token.")
    return token


def get_current_app_user(authorization: str | None) -> dict[str, str]:
    token = _extract_bearer_token(authorization)

    # Fresh client only for auth verification
    supabase = _create_supabase_client()
    response = supabase.auth.get_user(token)
    user = response.user

    if not user:
        raise ValueError("Invalid session. Please sign in again.")

    return {
        "id": user.id,
        "email": user.email or "",
    }


def _state_secret() -> bytes:
    settings = get_settings()
    return settings.supabase_service_role_key.encode("utf-8")


def create_google_state(user_id: str) -> str:
    payload = {
        "user_id": user_id,
        "ts": int(time.time()),
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    body = base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")

    sig = hmac.new(
        _state_secret(),
        body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return f"{body}.{sig}"


def read_google_state(state: str, max_age_seconds: int = 900) -> str:
    if not state or "." not in state:
        raise ValueError("Invalid OAuth state.")

    body, provided_sig = state.rsplit(".", 1)
    expected_sig = hmac.new(
        _state_secret(),
        body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(provided_sig, expected_sig):
        raise ValueError("Invalid OAuth state signature.")

    padded = body + "=" * (-len(body) % 4)
    payload = json.loads(base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8"))

    ts = int(payload.get("ts", 0))
    if int(time.time()) - ts > max_age_seconds:
        raise ValueError("OAuth state expired. Start Gmail connect again.")

    user_id = payload.get("user_id")
    if not user_id:
        raise ValueError("OAuth state missing user id.")

    return user_id


def save_gmail_account(user_id: str, gmail_email: str, refresh_token: str) -> None:
    # Fresh client only for admin DB write
    supabase = _create_supabase_client()

    response = (
        supabase.table("gmail_accounts")
        .upsert(
            {
                "user_id": user_id,
                "gmail_email": gmail_email,
                "google_refresh_token": refresh_token,
            },
            on_conflict="user_id",
        )
        .execute()
    )

    if getattr(response, "data", None) is None:
        raise RuntimeError("Failed to save Gmail account in Supabase.")


def get_gmail_account(user_id: str) -> dict | None:
    # Fresh client only for admin DB read
    supabase = _create_supabase_client()

    response = (
        supabase.table("gmail_accounts")
        .select("user_id, gmail_email, google_refresh_token, connected_at, updated_at")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    rows = response.data or []
    if not rows:
        return None
    return rows[0]
