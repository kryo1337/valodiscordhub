import { useEffect, useRef, useCallback } from "react";
import { create } from "zustand";
import { devtools } from "zustand/middleware";
import type { WebSocketEvent } from "@/types/events";
import { useQueueStore, useMatchStore, useLeaderboardStore } from "@/stores";

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000";

// --- Connection status store (shared across components) ---

export type ConnectionStatus =
  | "disconnected"
  | "connecting"
  | "connected"
  | "reconnecting";

interface ConnectionState {
  status: ConnectionStatus;
  isOnline: boolean;
  setStatus: (status: ConnectionStatus) => void;
  setOnline: (online: boolean) => void;
}

export const useConnectionStore = create<ConnectionState>()(
  devtools(
    (set) => ({
  status: "disconnected",
  isOnline: typeof navigator !== "undefined" ? navigator.onLine : true,
  setStatus: (status) => set({ status }),
  setOnline: (isOnline) => set({ isOnline }),
}),
    { name: "ConnectionStore" }
  )
);

// --- Hook ---

export function useWebSocket(token: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectDelayRef = useRef(1000);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const maxReconnectDelay = 60000;
  const maxReconnectAttempts = 20;
  const reconnectAttemptsRef = useRef(0);
  const intentionalCloseRef = useRef(false);

  const { setStatus, setOnline } = useConnectionStore();
  const { updateQueuePlayers } = useQueueStore();
  const { addMatch, updateMatch } = useMatchStore();
  const { setEntries } = useLeaderboardStore();

  const handleEvent = useCallback(
    (event: WebSocketEvent) => {
      switch (event.type) {
        case "queue_update":
          // Use updateQueuePlayers to match the exact players list from server
          updateQueuePlayers(event.rank_group, event.players);
          break;
        case "match_created":
          addMatch({
            match_id: event.match_id,
            rank_group: event.rank_group as
              | "iron-plat"
              | "dia-asc"
              | "imm-radiant",
            players_red: event.players_red,
            players_blue: event.players_blue,
            captain_red: event.captain_red,
            captain_blue: event.captain_blue,
            lobby_master: event.captain_red,
            defense_start: null,
            banned_maps: [],
            selected_map: null,
            red_score: null,
            blue_score: null,
            result: null,
            created_at: event.timestamp,
            ended_at: null,
          });
          break;
        case "match_updated":
          updateMatch(event.match_id, event.data);
          break;
        case "match_result":
          updateMatch(event.match_id, {
            result: event.result,
            red_score: event.red_score ?? null,
            blue_score: event.blue_score ?? null,
          });
          break;
        case "leaderboard_update":
          setEntries(event.rank_group, event.top_players);
          break;
        case "player_updated":
          // Player updates are handled by individual pages refetching
          // when they detect a relevant event
          break;
      }
    },
    [updateQueuePlayers, addMatch, updateMatch, setEntries]
  );

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const clearPingInterval = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!token) return;

    // Don't connect if already connected or connecting
    if (
      wsRef.current &&
      (wsRef.current.readyState === WebSocket.OPEN ||
        wsRef.current.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    const isReconnect = reconnectAttemptsRef.current > 0;
    setStatus(isReconnect ? "reconnecting" : "connecting");

    const wsUrl = `${WS_URL}/ws/${token}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setStatus("connected");
      reconnectDelayRef.current = 1000;
      reconnectAttemptsRef.current = 0;

      // Start ping interval
      clearPingInterval();
      pingIntervalRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send("ping");
        }
      }, 30000);
    };

    ws.onmessage = (event) => {
      try {
        if (event.data === "pong") return;
        const data = JSON.parse(event.data) as WebSocketEvent;
        handleEvent(data);
      } catch (e) {
        console.error("Failed to parse WebSocket message:", e);
      }
    };

    ws.onclose = (event) => {
      clearPingInterval();

      // Don't reconnect if we closed intentionally
      if (intentionalCloseRef.current) {
        setStatus("disconnected");
        return;
      }

      // Auth failure (1008 = Policy Violation, used by our API for bad tokens)
      if (event.code === 1008) {
        console.warn("WebSocket auth failed, not reconnecting with stale token");
        setStatus("disconnected");
        return;
      }

      // Max attempts reached
      if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
        console.warn("Max WebSocket reconnect attempts reached");
        setStatus("disconnected");
        return;
      }

      setStatus("reconnecting");
      reconnectAttemptsRef.current += 1;

      clearReconnectTimer();
      reconnectTimerRef.current = setTimeout(() => {
        connect();
      }, reconnectDelayRef.current);

      reconnectDelayRef.current = Math.min(
        reconnectDelayRef.current * 2,
        maxReconnectDelay
      );
    };

    ws.onerror = () => {
      // onclose will fire after onerror, so just log
      console.error("WebSocket connection error");
    };

    wsRef.current = ws;
  }, [token, handleEvent, setStatus, clearPingInterval, clearReconnectTimer]);

  // --- Online/offline detection ---
  useEffect(() => {
    const handleOnline = () => {
      setOnline(true);
      // Reconnect immediately when coming back online
      if (
        token &&
        wsRef.current?.readyState !== WebSocket.OPEN &&
        wsRef.current?.readyState !== WebSocket.CONNECTING
      ) {
        reconnectDelayRef.current = 1000;
        reconnectAttemptsRef.current = 0;
        connect();
      }
    };

    const handleOffline = () => {
      setOnline(false);
      setStatus("disconnected");
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [token, connect, setOnline, setStatus]);

  // --- Visibility change detection (reconnect when tab becomes visible) ---
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible" && token) {
        // Check if connection is stale
        if (
          wsRef.current?.readyState !== WebSocket.OPEN &&
          wsRef.current?.readyState !== WebSocket.CONNECTING
        ) {
          reconnectDelayRef.current = 1000;
          reconnectAttemptsRef.current = 0;
          connect();
        }
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [token, connect]);

  // --- Main connection effect ---
  useEffect(() => {
    if (!token) {
      setStatus("disconnected");
      return;
    }

    intentionalCloseRef.current = false;
    connect();

    return () => {
      intentionalCloseRef.current = true;
      clearPingInterval();
      clearReconnectTimer();
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [token, connect, setStatus, clearPingInterval, clearReconnectTimer]);

  return wsRef;
}
