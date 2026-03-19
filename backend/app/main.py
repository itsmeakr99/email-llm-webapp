from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.models import (
    DraftEmailRequest,
    DraftEmailResponse,
    GenerateAndSendRequest,
    HealthResponse,
    SendEmailRequest,
    SendEmailResponse,
)
from app.services.email_service import (
    build_google_auth_url_for_user,
    exchange_google_code_for_tokens,
    get_gmail_connection_status_for_user,
    send_email_via_gmail_for_user,
)
from app.services.llm_service import generate_email_draft
from app.settings import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name, version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        environment=settings.app_env,
    )


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "Email LLM API is running.",
        "docs": "/docs",
        "health": "/health",
        "google_auth_start": "/auth/google/start",
        "gmail_status": "/gmail/status",
    }


@app.get("/auth/google/start")
def google_auth_start(authorization: str | None = Header(default=None)) -> dict[str, str]:
    try:
        auth_url = build_google_auth_url_for_user(authorization)
        return {"auth_url": auth_url}
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to start Google OAuth: {exc}") from exc


@app.get("/auth/google/callback")
def google_auth_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
) -> RedirectResponse | dict[str, str]:
    if error:
        raise HTTPException(status_code=400, detail=f"Google OAuth failed: {error}")

    if not code:
        raise HTTPException(status_code=400, detail="Missing Google OAuth code.")

    if not state:
        raise HTTPException(status_code=400, detail="Missing Google OAuth state.")

    try:
        result = exchange_google_code_for_tokens(code, state)

        if settings.google_oauth_success_redirect_url:
            separator = "&" if "?" in settings.google_oauth_success_redirect_url else "?"
            redirect_to = f"{settings.google_oauth_success_redirect_url}{separator}gmail_connected=1"
            return RedirectResponse(url=redirect_to)

        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to complete Google OAuth: {exc}") from exc


@app.get("/gmail/status")
def gmail_status(authorization: str | None = Header(default=None)) -> dict[str, str | bool | None]:
    try:
        return get_gmail_connection_status_for_user(authorization)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read Gmail status: {exc}") from exc


@app.post("/draft-email", response_model=DraftEmailResponse)
def draft_email(request: DraftEmailRequest) -> DraftEmailResponse:
    try:
        draft = generate_email_draft(request)
        return DraftEmailResponse(
            draft=draft,
            preview_recipients=request.to,
            preview_cc=request.cc,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to draft email: {exc}") from exc


@app.post("/send-email", response_model=SendEmailResponse)
def send_email(
    request: SendEmailRequest,
    authorization: str | None = Header(default=None),
) -> SendEmailResponse:
    try:
        send_email_via_gmail_for_user(request, authorization)
        return SendEmailResponse(
            success=True,
            message="Email sent successfully.",
            to=request.to,
            cc=request.cc,
            bcc=request.bcc,
            subject=request.subject,
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {exc}") from exc


@app.post("/generate-and-send", response_model=SendEmailResponse)
def generate_and_send(
    request: GenerateAndSendRequest,
    authorization: str | None = Header(default=None),
) -> SendEmailResponse:
    try:
        draft = generate_email_draft(request)
        send_request = SendEmailRequest(
            to=request.to,
            cc=request.cc,
            bcc=request.bcc,
            subject=draft.subject,
            body=draft.body,
        )
        send_email_via_gmail_for_user(send_request, authorization)
        return SendEmailResponse(
            success=True,
            message="Email drafted and sent successfully.",
            to=send_request.to,
            cc=send_request.cc,
            bcc=send_request.bcc,
            subject=send_request.subject,
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate and send email: {exc}") from exc


@app.get("/debug-config")
def debug_config() -> dict[str, bool]:
    s = get_settings()
    return {
        "has_google_client_id": bool(s.google_client_id),
        "has_google_client_secret": bool(s.google_client_secret),
        "has_google_redirect_uri": bool(s.google_redirect_uri),
        "has_supabase_url": bool(s.supabase_url),
        "has_supabase_service_role_key": bool(s.supabase_service_role_key),
    }
