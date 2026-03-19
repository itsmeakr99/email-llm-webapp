"use client";

import { useState } from "react";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";

const supabase = createSupabaseBrowserClient();

export function AuthPanel() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleGoogleSignIn() {
    setBusy(true);
    setError("");

    try {
      const redirectTo =
        typeof window !== "undefined" ? window.location.origin : undefined;

      const { error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo,
        },
      });

      if (error) throw error;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Google sign-in failed.");
      setBusy(false);
    }
  }

  return (
    <div className="page-shell">
      <section className="hero-card">
        <div>
          <p className="eyebrow">Welcome</p>
          <h1>Sign in to use your AI email workspace.</h1>
          <p className="hero-copy">
            Continue with your Google account. After login, you can connect your Gmail to send emails from your own inbox.
          </p>
        </div>
      </section>

      <section className="workbench-grid">
        <div className="panel">
          <div className="panel-header">
            <h2>Continue with Google</h2>
          </div>

          <div className="form-grid">
            {error ? <div className="error-box">{error}</div> : null}

            <div className="action-row">
              <button
                type="button"
                className="primary-button"
                onClick={handleGoogleSignIn}
                disabled={busy}
              >
                {busy ? "Redirecting..." : "Continue with Google"}
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
