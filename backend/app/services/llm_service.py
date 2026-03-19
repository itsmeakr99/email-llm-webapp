from openai import OpenAI
from app.models import DraftEmailRequest, EmailDraft
from app.settings import get_settings


SYSTEM_PROMPT = """
You write polished outbound emails.
Always produce:
- a clear subject line
- a concise body
- natural formatting with greeting, short paragraphs, and sign-off when appropriate
Rules:
- Keep the email aligned to the user's purpose and source content.
- Do not invent facts not present in the user input.
- Keep tone consistent with the requested tone.
- Keep the email within the requested length as much as possible.
- Return only the structured draft fields.
""".strip()


def build_user_prompt(request: DraftEmailRequest) -> str:
    recipients = ", ".join(request.to) if request.to else "Not provided"
    cc = ", ".join(request.cc) if request.cc else "None"
    sender_name = request.sender_name or "Not provided"
    extra = request.additional_instructions or "None"

    return f"""
Draft an email from the following details.

Purpose:
{request.purpose}

Tone:
{request.tone}

Sender name:
{sender_name}

To:
{recipients}

CC:
{cc}

Maximum words:
{request.max_words}

Additional instructions:
{extra}

Source content / notes:
{request.content}
""".strip()


def generate_email_draft(request: DraftEmailRequest) -> EmailDraft:
    settings = get_settings()

    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is not configured.")

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.responses.parse(
        model=settings.openai_model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(request)},
        ],
        text_format=EmailDraft,
    )

    if not response.output_parsed:
        raise RuntimeError("Model did not return a structured email draft.")

    return response.output_parsed
