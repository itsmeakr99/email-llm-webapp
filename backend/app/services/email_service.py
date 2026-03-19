import html
import json
from urllib import error, request as urllib_request

from app.models import SendEmailRequest
from app.settings import get_settings


def _build_from_header(from_email: str, from_name: str) -> str:
    from_name = (from_name or "").strip()
    if from_name:
        return f"{from_name} <{from_email}>"
    return from_email


def _text_to_html(text: str) -> str:
    escaped = html.escape(text or "")
    return f"<div>{escaped.replace(chr(10), '<br>')}</div>"


def send_email_via_resend(request: SendEmailRequest) -> None:
    settings = get_settings()

    required = {
        "RESEND_API_KEY": settings.resend_api_key,
        "RESEND_FROM_EMAIL": settings.resend_from_email,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise ValueError(f"Missing Resend configuration: {', '.join(missing)}")

    payload = {
        "from": _build_from_header(
            settings.resend_from_email,
            settings.resend_from_name,
        ),
        "to": request.to,
        "subject": request.subject,
        "html": _text_to_html(request.body),
    }

    if request.cc:
        payload["cc"] = request.cc

    if request.bcc:
        payload["bcc"] = request.bcc

    req = urllib_request.Request(
        url="https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib_request.urlopen(req, timeout=30) as response:
            response_body = response.read().decode("utf-8")
            if response.status >= 400:
                raise RuntimeError(f"Resend API error: {response_body}")

            parsed = json.loads(response_body) if response_body else {}
            if not parsed.get("id"):
                raise RuntimeError(f"Unexpected Resend response: {response_body}")

    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        try:
            parsed = json.loads(body) if body else {}
            message = parsed.get("message") or parsed.get("error") or body
        except Exception:
            message = body or str(exc)
        raise RuntimeError(f"Resend API request failed: {message}") from exc

    except error.URLError as exc:
        raise RuntimeError(f"Could not reach Resend API: {exc.reason}") from exc
