"use client";

import { FormEvent, useState } from "react";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";

const supabase = createSupabaseBrowserClient();

export function AuthPanel() {
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");

    try {
      if (mode === "signup") {
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
          options: {
            emailRedirectTo:
              typeof window !== "undefined" ? window.location.origin : undefined,
            data: {
              full_name: fullName,
            },
          },
        });

        if (error) throw error;

        if (data.session) {
          setMessage("Account created and you are signed in.");
        } else {
          setMessage(
            "Account created. Check your email, click the confirmation link, then come back and sign in."
          );
        }
      } else {
        const { error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });

        if (error) throw error;

        setMessage("Signed in successfully.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed.");
    } finally {
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
            This is the first step toward making the app work for any user, not just one Gmail account.
          </p>
        </div>
      </section>

      <section className="workbench-grid">
        <div className="panel">
          <div className="panel-header">
            <h2>{mode === "signin" ? "Sign in" : "Create account"}</h2>
            <div className="header-actions">
              <button
                type="button"
                className={mode === "signin" ? "secondary-button" : "ghost-button"}
                onClick={() => {
                  setMode("signin");
                  setError("");
                  setMessage("");
                }}
              >
                Sign in
              </button>
              <button
                type="button"
                className={mode === "signup" ? "secondary-button" : "ghost-button"}
                onClick={() => {
                  setMode("signup");
                  setError("");
                  setMessage("");
                }}
              >
                Sign up
              </button>
            </div>
          </div>

          <form className="form-grid" onSubmit={handleSubmit}>
            {mode === "signup" ? (
              <label className="full-width">
                Full name
                <input
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Anil Kumar Reddy"
                />
              </label>
            ) : null}

            <label className="full-width">
              Email
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
              />
            </label>

            <label className="full-width">
              Password
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 6 characters"
              />
            </label>

            {message ? <div className="stat-card">{message}</div> : null}
            {error ? <div className="error-box">{error}</div> : null}

            <div className="action-row">
              <button
                type="submit"
                className="primary-button"
                disabled={busy || !email.trim() || !password.trim()}
              >
                {busy
                  ? "Please wait..."
                  : mode === "signin"
                  ? "Sign in"
                  : "Create account"}
              </button>
            </div>
          </form>
        </div>
      </section>
    </div>
  );
}
