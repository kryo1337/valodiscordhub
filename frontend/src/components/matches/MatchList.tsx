import { MatchCard } from "./MatchCard";
import { EmptyState } from "@/components/common";
import { Swords } from "lucide-react";
import type { Match } from "@/types/api";

interface MatchListProps {
  matches: Match[];
  onMatchClick?: (match: Match) => void;
  emptyMessage?: string;
}

export function MatchList({
  matches,
  onMatchClick,
  emptyMessage = "No matches found",
}: MatchListProps) {
  if (matches.length === 0) {
    return (
      <EmptyState
        icon={<Swords className="h-16 w-16" />}
        title={emptyMessage}
        description="Matches will appear here when players create them"
      />
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {matches.map((match) => (
        <MatchCard
          key={match.match_id}
          match={match}
          onClick={() => onMatchClick?.(match)}
        />
      ))}
    </div>
  );
}
