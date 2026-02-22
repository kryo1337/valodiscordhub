import { useConnectionStore } from "@/hooks/useWebSocket";
import { WifiOff, RefreshCw } from "lucide-react";
import { cn } from "@/lib/cn";

export function ConnectionStatus() {
  const { status, isOnline } = useConnectionStore();

  if (!isOnline) {
    return (
      <div
        className="bg-valorant-red text-white text-xs text-center py-3 px-4 flex items-center justify-center gap-3"
        role="status"
        aria-live="polite"
      >
        <WifiOff className="h-4 w-4" />
        <span className="uppercase tracking-wider font-bold">
          Offline — Reconnecting...
        </span>
      </div>
    );
  }

  if (status === "reconnecting") {
    return (
      <div
        className="bg-valorant-gold text-valorant-darker text-xs text-center py-3 px-4 flex items-center justify-center gap-3"
        role="status"
        aria-live="polite"
      >
        <RefreshCw className="h-4 w-4 animate-spin" />
        <span className="uppercase tracking-wider font-bold">
          Reconnecting...
        </span>
      </div>
    );
  }

  if (status === "connecting") {
    return (
      <div
        className="bg-valorant-dark text-valorant-gray text-xs text-center py-3 px-4 flex items-center justify-center gap-3 border-b border-valorant-gray/20"
        role="status"
        aria-live="polite"
      >
        <RefreshCw className="h-4 w-4 animate-spin" />
        <span className="uppercase tracking-wider font-bold">
          Connecting...
        </span>
      </div>
    );
  }

  return null;
}
