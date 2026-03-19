"use client";

import { useEffect, useMemo, useState } from "react";
import type { User } from "@supabase/supabase-js";
import {
  draftEmail,
  getGmailStatus,
  getGoogleAuthUrl,
  healthCheck,
  sendEmail,
} from "@/lib/api";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";
import { AuthPanel } from "@/components/auth-panel";

const supabase = createSupabaseBrowserClient();

type FormState = {
  to: string;
  cc: string;
  bcc: string;
  purpose: string;
  tone: string;
  senderName: string;
  additionalInstructions: string;
  maxWords: number;
  content: string;
  subject: string;
  body: string;
};

const initialState: FormState = {
  to: "",
  cc: "",
  bcc: "",
  purpose: "",
  tone: "professional",
  senderName: "",
  additionalInstructions: "",
  maxWords: 180,
  content: "",
  subject: "",
  body: "",
};

function splitEmails(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function localStorageAvailable(): boolean {
  return typeof window !== "undefined";
}

export function EmailWorkbench() {
  const [user, setUser] = useState<User | null>(null);
  const [authReady, setAuthReady] = useState(false);

  const [form, setForm] = useState<FormState>(initialState);
  const [isDrafting, setIsDrafting] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [isConnectingGmail, setIsConnectingGmail] = useState(false);
  const [status, setStatus] = useState<string>("Ready");
  const [error, setError] = useState<string>("");
  const [apiState, setApiState] = useState<string>("Checking backend...");
  const [gmailConnected, setGmailConnected] = useState(false);
  const [connectedGmailEmail, setConnectedGmailEmail] = useState<string | null>(null);

  useEffect(() => {
    healthCheck()
      .then((data) =>
        setApiState(`Backend connected · ${data.app} (${data.environment})`)
      )
      .catch(() =>
        setApiState(
          "Backend not reachable. Start FastAPI on port 8000 or update NEXT_PUBLIC_API_BASE_URL."
        )
      );
  }, []);

  useEffect(() => {
    let mounted = true;

    supabase.auth.getUser().then(({ data }) => {
      if (!mounted) return;
      setUser(data.user ?? null);
      setAuthReady(true);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      setAuthReady(true);
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, []);

  useEffect(() => {
    if (!user || !localStorageAvailable()) return;

    const storageKey = `email-llm-draft-form:${user.id}`;
    const saved = window.localStorage.getItem(storageKey);

    if (saved) {
      try {
        const parsed = JSON.parse(saved) as FormState;
        setForm(parsed);
        return;
      } catch {
        // ignore malformed saved data
      }
    }

    const suggestedName =
      typeof user.user_metadata?.full_name === "string"
        ? user.user_metadata.full_name
        : "";

    setForm((current) => ({
      ...current,
      senderName: current.senderName || suggestedName,
    }));
  }, [user]);

  useEffect(() => {
    if (!user || !localStorageAvailable()) return;
    const storageKey = `email-llm-draft-form:${user.id}`;
    window.localStorage.setItem(storageKey, JSON.stringify(form));
  }, [form, user]);

  useEffect(() => {
    if (!user) {
      setGmailConnected(false);
      setConnectedGmailEmail(null);
      return;
    }

    async function loadGmailStatus() {
      try {
        const { data } = await supabase.auth.getSession();
        const accessToken = data.session?.access_token;
        if (!accessToken) return;

        const result = await getGmailStatus(accessToken);
        setGmailConnected(result.connected);
        setConnectedGmailEmail(result.gmail_email);
      } catch {
        setGmailConnected(false);
        setConnectedGmailEmail(null);
      }
    }

    loadGmailStatus();
  }, [user]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("gmail_connected") === "1") {
      setStatus("Gmail connected successfully.");
      setError("");
      window.history.replaceState({}, "", window.location.pathname);
      if (user) {
        supabase.auth.getSession().then(async ({ data }) => {
          const accessToken = data.session?.access_token;
          if (!accessToken) return;
          const result = await getGmailStatus(accessToken);
          setGmailConnected(result.connected);
          setConnectedGmailEmail(result.gmail_email);
        });
      }
    }
  }, [user]);

  const recipientCount = useMemo(() => splitEmails(form.to).length, [form.to]);

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function handleDraft() {
    setError("");
    setStatus("Generating draft...");
    setIsDrafting(true);

    try {
      const response = await draftEmail({
        to: splitEmails(form.to),
        cc: splitEmails(form.cc),
        purpose: form.purpose,
        content: form.content,
        tone: form.tone,
        sender_name: form.senderName || undefined,
        additional_instructions: form.additionalInstructions || undefined,
        max_words: form.maxWords,
      });

      setForm((current) => ({
        ...current,
        subject: response.draft.subject,
        body: response.draft.body,
      }));
      setStatus("Draft ready. Review it and send when you are happy with it.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate draft.");
      setStatus("Draft failed.");
    } finally {
      setIsDrafting(false);
    }
  }

  async function handleSend() {
    setError("");
    setStatus("Sending email...");
    setIsSending(true);

    try {
      const { data } = await supabase.auth.getSession();
      const accessToken = data.session?.access_token;

      if (!accessToken) {
        throw new Error("You are not signed in. Please sign in again.");
      }

      if (!gmailConnected) {
        throw new Error("Connect your Gmail account before sending email.");
      }

      const response = await sendEmail(
        {
          to: splitEmails(form.to),
          cc: splitEmails(form.cc),
          bcc: splitEmails(form.bcc),
          subject: form.subject,
          body: form.body,
        },
        accessToken
      );

      setStatus(`${response.message} Subject: ${response.subject}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send email.");
      setStatus("Send failed.");
    } finally {
      setIsSending(false);
    }
  }

  async function handleConnectGmail() {
    setError("");
    setStatus("Starting Gmail connection...");
    setIsConnectingGmail(true);

    try {
      const { data } = await supabase.auth.getSession();
      const accessToken = data.session?.access_token;

      if (!accessToken) {
        throw new Error("You are not signed in. Please sign in again.");
      }

      const result = await getGoogleAuthUrl(accessToken);
      window.location.href = result.auth_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start Gmail connection.");
      setStatus("Gmail connection failed.");
      setIsConnectingGmail(false);
    }
  }

  function loadSample() {
    setForm({
      ...initialState,
      to: "client@example.com",
      purpose: "Follow up after project discussion",
      tone: "warm and professional",
      senderName:
        typeof user?.user_metadata?.full_name === "string"
          ? user.user_metadata.full_name
          : "",
      additionalInstructions: "Keep it crisp, confident, and client-friendly.",
      maxWords: 160,
      content:
        "Thank them for the meeting, mention that the API and UI starter are ready, and say I can share the next iteration with authentication and dashboard tracking.",
      subject: "",
      body: "",
    });
    setStatus("Sample content loaded.");
    setError("");
  }

  function clearAll() {
    setForm({
      ...initialState,
      senderName:
        typeof user?.user_metadata?.full_name === "string"
          ? user.user_metadata.full_name
          : "",
    });
    setStatus("Form cleared.");
    setError("");

    if (user && localStorageAvailable()) {
      window.localStorage.removeItem(`email-llm-draft-form:${user.id}`);
    }
  }

  async function handleSignOut() {
    await supabase.auth.signOut();
  }

  const disableDraft =
    isDrafting || !form.purpose.trim() || !form.content.trim() || recipientCount === 0;

  const disableSend =
    isSending ||
    !form.subject.trim() ||
    !form.body.trim() ||
    splitEmails(form.to).length === 0 ||
    !gmailConnected;

  if (!authReady) {
    return (
      <div className="page-shell">
        <section className="hero-card">
          <div>
            <p className="eyebrow">Loading</p>
            <h1>Checking your session...</h1>
          </div>
        </section>
      </div>
    );
  }

  if (!user) {
    return <AuthPanel />;
  }

  return (
    <div className="page-shell">
      <section className="hero-card">
        <div>
          <p className="eyebrow">AI Email Assistant</p>
          <h1>Draft, review, and send emails from one clean web page.</h1>
          <p className="hero-copy">
            You are signed in as <strong>{user.email}</strong>.
          </p>
        </div>
        <div className="hero-status-grid">
          <div className="stat-card">
            <span>Status</span>
            <strong>{status}</strong>
          </div>
          <div className="stat-card">
            <span>Backend</span>
            <strong>{apiState}</strong>
          </div>
          <div className="stat-card">
            <span>Recipients</span>
            <strong>{recipientCount}</strong>
          </div>
          <div className="stat-card">
            <span>Gmail</span>
            <strong>
              {gmailConnected
                ? `Connected: ${connectedGmailEmail ?? "Connected"}`
                : "Not connected"}
            </strong>
          </div>
        </div>
      </section>

      <section className="workbench-grid">
        <div className="panel">
          <div className="panel-header">
            <h2>Email details</h2>
            <div className="header-actions">
              <button
                type="button"
                className="secondary-button"
                onClick={loadSample}
              >
                Load sample
              </button>
              <button
                type="button"
                className="secondary-button"
                onClick={handleConnectGmail}
                disabled={isConnectingGmail}
              >
                {isConnectingGmail
                  ? "Connecting..."
                  : gmailConnected
                  ? "Reconnect Gmail"
                  : "Connect Gmail"}
              </button>
              <button type="button" className="ghost-button" onClick={clearAll}>
                Clear
              </button>
              <button
                type="button"
                className="ghost-button"
                onClick={handleSignOut}
              >
                Sign out
              </button>
            </div>
          </div>

          <div className="form-grid">
            <label>
              To (comma-separated)
              <input
                value={form.to}
                onChange={(e) => update("to", e.target.value)}
                placeholder="alice@example.com, bob@example.com"
              />
            </label>

            <label>
              CC
              <input
                value={form.cc}
                onChange={(e) => update("cc", e.target.value)}
                placeholder="manager@example.com"
              />
            </label>

            <label>
              BCC
              <input
                value={form.bcc}
                onChange={(e) => update("bcc", e.target.value)}
                placeholder="internal@example.com"
              />
            </label>

            <label>
              Tone
              <select
                value={form.tone}
                onChange={(e) => update("tone", e.target.value)}
              >
                <option value="professional">Professional</option>
                <option value="warm and professional">Warm and professional</option>
                <option value="friendly">Friendly</option>
                <option value="formal">Formal</option>
                <option value="persuasive">Persuasive</option>
              </select>
            </label>

            <label>
              Purpose
              <input
                value={form.purpose}
                onChange={(e) => update("purpose", e.target.value)}
                placeholder="Interview follow-up"
              />
            </label>

            <label>
              Sender name
              <input
                value={form.senderName}
                onChange={(e) => update("senderName", e.target.value)}
                placeholder="Anil Kumar Reddy"
              />
            </label>

            <label className="full-width">
              Additional instructions
              <input
                value={form.additionalInstructions}
                onChange={(e) =>
                  update("additionalInstructions", e.target.value)
                }
                placeholder="Mention attached proposal, keep under 150 words, include clear CTA"
              />
            </label>

            <label>
              Max words
              <input
                type="number"
                min={40}
                max={1200}
                value={form.maxWords}
                onChange={(e) => update("maxWords", Number(e.target.value || 180))}
              />
            </label>

            <label className="full-width">
              Raw content / notes
              <textarea
                value={form.content}
                onChange={(e) => update("content", e.target.value)}
                placeholder="Write the main points you want the email to say..."
                rows={10}
              />
            </label>
          </div>

          <div className="action-row">
            <button
              type="button"
              className="primary-button"
              disabled={disableDraft}
              onClick={handleDraft}
            >
              {isDrafting ? "Generating..." : "Generate draft"}
            </button>
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <h2>Draft preview</h2>
            <p>Edit the result before sending.</p>
          </div>

          <div className="form-grid">
            <label className="full-width">
              Subject
              <input
                value={form.subject}
                onChange={(e) => update("subject", e.target.value)}
                placeholder="Generated subject will appear here"
              />
            </label>

            <label className="full-width">
              Body
              <textarea
                value={form.body}
                onChange={(e) => update("body", e.target.value)}
                placeholder="Generated email body will appear here"
                rows={16}
              />
            </label>
          </div>

          {error ? <div className="error-box">{error}</div> : null}

          <div className="action-row">
            <button
              type="button"
              className="primary-button"
              disabled={disableSend}
              onClick={handleSend}
            >
              {isSending ? "Sending..." : gmailConnected ? "Send email" : "Connect Gmail to send"}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
