"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import type { DashboardSnapshot } from "@/types/trading";
import { getAccessToken } from "@/lib/api";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws";

type ConnectionState = "connecting" | "live" | "offline";

type WsContextValue = {
  data: DashboardSnapshot | null;
  connectionState: ConnectionState;
};

const WsContext = createContext<WsContextValue>({
  data: null,
  connectionState: "offline",
});

export function useLiveData() {
  return useContext(WsContext);
}

export function WsProvider({ children }: { children: React.ReactNode }) {
  const [data, setData] = useState<DashboardSnapshot | null>(null);
  const [connectionState, setConnectionState] = useState<ConnectionState>("offline");
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  const connect = useCallback(() => {
    const token = getAccessToken();
    if (!token) {
      setConnectionState("offline");
      return;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setConnectionState("connecting");
    const ws = new WebSocket(`${WS_URL}?token=${token}`);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) return;
      setConnectionState("live");
    };

    ws.onmessage = (event) => {
      if (!mountedRef.current) return;
      try {
        const msg = JSON.parse(event.data);
        if (msg.payload) {
          setData(msg.payload as DashboardSnapshot);
        }
      } catch {
        // ignore unparseable messages
      }
    };

    ws.onclose = () => {
      if (!mountedRef.current) return;
      setConnectionState("offline");
      wsRef.current = null;
      reconnectRef.current = setTimeout(connect, 5000);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return (
    <WsContext.Provider value={{ data, connectionState }}>
      {children}
    </WsContext.Provider>
  );
}
