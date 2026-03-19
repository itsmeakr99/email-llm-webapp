import smtplib
from email.message import EmailMessage
from app.models import SendEmailRequest
from app.settings import get_settings



def send_email_via_smtp(request: SendEmailRequest) -> None:
    settings = get_settings()

    required = {
        "SMTP_HOST": settings.smtp_host,
        "SMTP_USERNAME": settings.smtp_username,
        "SMTP_PASSWORD": settings.smtp_password,
        "SMTP_FROM_EMAIL": settings.smtp_from_email,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise ValueError(f"Missing SMTP configuration: {', '.join(missing)}")

    msg = EmailMessage()
    from_name = settings.smtp_from_name.strip()
    msg["From"] = f"{from_name} <{settings.smtp_from_email}>" if from_name else settings.smtp_from_email
    msg["To"] = ", ".join(request.to)
    if request.cc:
        msg["Cc"] = ", ".join(request.cc)
    msg["Subject"] = request.subject
    msg.set_content(request.body)

    all_recipients = list(request.to) + list(request.cc) + list(request.bcc)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
        server.ehlo()
        if settings.smtp_use_tls:
            server.starttls()
            server.ehlo()
        server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(msg, from_addr=settings.smtp_from_email, to_addrs=all_recipients)
