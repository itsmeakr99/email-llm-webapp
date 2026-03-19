export type DraftRequest = {
  to: string[];
  cc: string[];
  purpose: string;
  content: string;
  tone: string;
  sender_name?: string;
  additional_instructions?: string;
  max_words: number;
};

export type DraftResponse = {
  draft: {
    subject: string;
    body: string;
  };
  preview_recipients: string[];
  preview_cc: string[];
};

export type SendRequest = {
  to: string[];
  cc: string[];
  bcc: string[];
  subject: string;
  body: string;
};

export type SendResponse = {
  success: boolean;
  message: string;
  to: string[];
  cc: string[];
  bcc: string[];
  subject: string;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    },
    cache: "no-store"
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(data.detail ?? "Request failed");
  }

  return response.json() as Promise<T>;
}

export async function draftEmail(payload: DraftRequest): Promise<DraftResponse> {
  return apiFetch<DraftResponse>("/draft-email", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function sendEmail(payload: SendRequest): Promise<SendResponse> {
  return apiFetch<SendResponse>("/send-email", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function healthCheck(): Promise<{ status: string; app: string; environment: string }> {
  return apiFetch<{ status: string; app: string; environment: string }>("/health");
}
