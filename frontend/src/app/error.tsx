"use client";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-ink-950 px-6 text-center">
      <p className="font-mono text-sm tracking-[0.18em] text-warn">ALPHAFORGE</p>
      <h1 className="text-xl">Something broke</h1>
      <p className="max-w-md text-sm text-mute">{error.message}</p>
      <button
        type="button"
        onClick={reset}
        className="rounded bg-warn px-4 py-2 text-sm font-medium text-ink-950"
      >
        Retry
      </button>
    </div>
  );
}
