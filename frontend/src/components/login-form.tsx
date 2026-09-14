"use client";

import { FormEvent, useState } from "react";
import { api, setTokens } from "@/lib/api";

export function LoginForm({ onSignedIn }: { onSignedIn?: () => void }) {
  const [email, setEmail] = useState("operator@localhost");
  const [password, setPassword] = useState("change-me");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const tokens = await api.login(email, password);
      setTokens(tokens);
      if (onSignedIn) {
        onSignedIn();
      } else {
        window.location.assign("/");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-ink-950 px-4">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm rounded-lg border border-line bg-ink-900 p-6"
      >
        <div className="mb-6 font-mono text-sm tracking-[0.18em] text-warn">ALPHAFORGE</div>
        <h1 className="mb-4 text-lg">Operator sign-in</h1>
        <label className="mb-3 block text-sm text-mute">
          Email
          <input
            className="mt-1 w-full rounded border border-line bg-ink-800 px-3 py-2 text-white"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            type="email"
            required
          />
        </label>
        <label className="mb-4 block text-sm text-mute">
          Password
          <input
            className="mt-1 w-full rounded border border-line bg-ink-800 px-3 py-2 text-white"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
            required
          />
        </label>
        {error ? <p className="mb-3 text-sm text-loss">{error}</p> : null}
        <button
          disabled={busy}
          className="w-full rounded bg-warn px-4 py-2 text-sm font-medium text-ink-950 disabled:opacity-50"
        >
          {busy ? "Signing in…" : "Enter"}
        </button>
      </form>
    </div>
  );
}
