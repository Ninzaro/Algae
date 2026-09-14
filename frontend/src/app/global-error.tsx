"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body style={{ background: "#07090c", color: "#e8eef7", fontFamily: "sans-serif" }}>
        <div style={{ padding: 48 }}>
          <p>AlphaForge failed to load.</p>
          <p style={{ color: "#8b9bb4" }}>{error.message}</p>
          <button type="button" onClick={reset} style={{ marginTop: 16 }}>
            Retry
          </button>
        </div>
      </body>
    </html>
  );
}
