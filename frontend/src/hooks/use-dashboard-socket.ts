"use client";

import { useEffect, useRef, useState } from "react";
import { getAccessToken } from "@/lib/api";
import type { DashboardSnapshot } from "@/types/trading";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws";

export type SocketState = "off" | "connecting" | "live" | "down";

export function useDashboardSocket(
  enabled: boolean,
  onSnapshot: (data: DashboardSnapshot) => void,
): SocketState {
  const [state, setState] = useState<SocketState>("off");
  const onSnapshotRef = useRef(onSnapshot);
  onSnapshotRef.current = onSnapshot;

  useEffect(() => {
    if (!enabled) {
      setState("off");
      return;
    }
    const token = getAccessToken();
    if (!token) {
      setState("off");
      return;
    }

    let closed = false;
    let socket: WebSocket | null = null;
    let retry: ReturnType<typeof setTimeout> | undefined;
    let delay = 1000;

    function connect() {
      if (closed) return;
      setState("connecting");
      const url = `${WS_BASE}?token=${encodeURIComponent(token as string)}`;
      socket = new WebSocket(url);
      socket.onopen = () => {
        delay = 1000;
        setState("live");
      };
      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as {
            event?: string;
            payload?: DashboardSnapshot;
          };
          if (message.payload && typeof message.payload === "object" && "account" in message.payload) {
            onSnapshotRef.current(message.payload);
          }
        } catch {
          /* ignore malformed frames */
        }
      };
      socket.onerror = () => {
        socket?.close();
      };
      socket.onclose = () => {
        setState("down");
        if (!closed) {
          retry = setTimeout(connect, delay);
          delay = Math.min(delay * 2, 15000);
        }
      };
    }

    connect();
    return () => {
      closed = true;
      if (retry) clearTimeout(retry);
      socket?.close();
    };
  }, [enabled]);

  return state;
}
