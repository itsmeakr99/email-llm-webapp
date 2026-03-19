from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class DraftEmailRequest(BaseModel):
    to: List[EmailStr] = Field(default_factory=list)
    cc: List[EmailStr] = Field(default_factory=list)
    purpose: str = Field(..., description="Why this email is being written")
    content: str = Field(..., description="The raw content or notes to turn into an email")
    tone: str = Field(default="professional")
    sender_name: Optional[str] = None
    additional_instructions: Optional[str] = None
    max_words: int = Field(default=220, ge=40, le=1200)


class SendEmailRequest(BaseModel):
    to: List[EmailStr]
    subject: str
    body: str
    cc: List[EmailStr] = Field(default_factory=list)
    bcc: List[EmailStr] = Field(default_factory=list)


class GenerateAndSendRequest(DraftEmailRequest):
    send_immediately: bool = True
    bcc: List[EmailStr] = Field(default_factory=list)


class EmailDraft(BaseModel):
    subject: str
    body: str


class DraftEmailResponse(BaseModel):
    draft: EmailDraft
    preview_recipients: List[EmailStr] = Field(default_factory=list)
    preview_cc: List[EmailStr] = Field(default_factory=list)


class SendEmailResponse(BaseModel):
    success: bool
    message: str
    to: List[EmailStr]
    cc: List[EmailStr] = Field(default_factory=list)
    bcc: List[EmailStr] = Field(default_factory=list)
    subject: str


class HealthResponse(BaseModel):
    status: str
    app: str
    environment: str
