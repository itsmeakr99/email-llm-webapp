const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://127.0.0.1:8000";

type DraftEmailRequest = {
  to: string[];
  cc: string[];
  purpose: string;
  content: string;
  tone: string;
  sender_name?: string;
  additional_instructions?: string;
  max_words: number;
};

type DraftEmailResponse = {
  draft: {
    subject: string;
    body: string;
  };
  preview_recipients: string[];
  preview_cc: string[];
};

type SendEmailRequest = {
  to: string[];
  cc: string[];
  bcc: string[];
  subject: string;
  body: string;
};

type SendEmailResponse = {
  success: boolean;
  message: string;
  to: string[];
  cc: string[];
  bcc: string[];
  subject: string;
};

type HealthResponse = {
  status: string;
  app: string;
  environment: string;
};

type GmailStatusResponse = {
  connected: boolean;
  gmail_email: string | null;
};

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const data = await response.json();
      detail = data.detail ?? detail;
    } catch {
      // ignore JSON parse errors
    }
    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}

export async function healthCheck(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`, {
    method: "GET",
  });

  return parseResponse<HealthResponse>(response);
}

export async function draftEmail(payload: DraftEmailRequest): Promise<DraftEmailResponse> {
  const response = await fetch(`${API_BASE_URL}/draft-email`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  return parseResponse<DraftEmailResponse>(response);
}

export async function sendEmail(
  payload: SendEmailRequest,
  accessToken: string
): Promise<SendEmailResponse> {
  const response = await fetch(`${API_BASE_URL}/send-email`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(payload),
  });

  return parseResponse<SendEmailResponse>(response);
}

export async function getGmailStatus(
  accessToken: string
): Promise<GmailStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/gmail/status`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  return parseResponse<GmailStatusResponse>(response);
}

export async function getGoogleAuthUrl(
  accessToken: string
): Promise<{ auth_url: string }> {
  const response = await fetch(`${API_BASE_URL}/auth/google/start`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  return parseResponse<{ auth_url: string }>(response);
}
