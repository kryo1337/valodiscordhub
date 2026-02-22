import { MatchHistoryCard } from "./MatchHistoryCard";
import { EmptyState } from "@/components/common";
import { History } from "lucide-react";
import type { Match } from "@/types/api";

interface HistoryListProps {
  matches: Match[];
  userDiscordId?: string;
}

export function HistoryList({ matches, userDiscordId }: HistoryListProps) {
  if (matches.length === 0) {
    return (
      <EmptyState
        icon={<History className="h-16 w-16" />}
        title="No match history"
        description="Your completed matches will appear here"
      />
    );
  }

  return (
    <div className="space-y-4">
      {matches.map((match) => (
        <MatchHistoryCard
          key={match.match_id}
          match={match}
          userDiscordId={userDiscordId}
        />
      ))}
    </div>
  );
}
