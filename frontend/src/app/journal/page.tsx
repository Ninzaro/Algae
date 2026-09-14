"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Shell } from "@/components/shell";
import { api, getAccessToken } from "@/lib/api";
import { formatTs } from "@/lib/utils";
import type { JournalEntry } from "@/types/trading";

export default function JournalPage() {
  const router = useRouter();
  const [items, setItems] = useState<JournalEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getAccessToken()) {
      router.replace("/login");
      return;
    }
    api
      .journal()
      .then((page) => setItems(page.items))
      .catch((err: Error) => setError(err.message));
  }, [router]);

  return (
    <Shell>
      <h1 className="mb-4 text-xl font-medium">Decision journal</h1>
      <p className="mb-6 text-sm text-mute">Append-only audit trail. Entries are never mutated.</p>
      {error ? <p className="text-loss">{error}</p> : null}
      <div className="overflow-x-auto rounded-lg border border-line">
        <table className="w-full text-left text-sm">
          <thead className="bg-ink-900 text-xs uppercase text-mute">
            <tr>
              <th className="px-3 py-2">Time</th>
              <th className="px-3 py-2">Event</th>
              <th className="px-3 py-2">Payload</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="border-t border-line">
                <td className="whitespace-nowrap px-3 py-2 font-mono text-mute">
                  {formatTs(item.timestamp)}
                </td>
                <td className="px-3 py-2 font-mono">{item.event_type}</td>
                <td className="px-3 py-2 font-mono text-xs text-mute">
                  {JSON.stringify(item.payload).slice(0, 180)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
