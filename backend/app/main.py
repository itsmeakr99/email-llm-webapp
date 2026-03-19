from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.models import (
    DraftEmailRequest,
    DraftEmailResponse,
    GenerateAndSendRequest,
    HealthResponse,
    SendEmailRequest,
    SendEmailResponse,
)
from app.services.email_service import send_email_via_smtp
from app.services.llm_service import generate_email_draft
from app.settings import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name, version="1.1.0")

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
    }


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
def send_email(request: SendEmailRequest) -> SendEmailResponse:
    try:
        send_email_via_smtp(request)
        return SendEmailResponse(
            success=True,
            message="Email sent successfully.",
            to=request.to,
            cc=request.cc,
            bcc=request.bcc,
            subject=request.subject,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {exc}") from exc


@app.post("/generate-and-send", response_model=SendEmailResponse)
def generate_and_send(request: GenerateAndSendRequest) -> SendEmailResponse:
    try:
        draft = generate_email_draft(request)
        send_request = SendEmailRequest(
            to=request.to,
            cc=request.cc,
            bcc=request.bcc,
            subject=draft.subject,
            body=draft.body,
        )
        send_email_via_smtp(send_request)
        return SendEmailResponse(
            success=True,
            message="Email drafted and sent successfully.",
            to=send_request.to,
            cc=send_request.cc,
            bcc=send_request.bcc,
            subject=send_request.subject,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate and send email: {exc}") from exc
