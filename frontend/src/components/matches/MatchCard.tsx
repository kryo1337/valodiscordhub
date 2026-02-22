import { Swords, Clock, MapPin, Trophy } from "lucide-react";
import { Card, CardHeader, CardContent, Badge } from "@/components/ui";
import { formatRelativeTime, formatRankGroupShort, formatScore } from "@/lib/format";
import { cn } from "@/lib/cn";
import type { Match } from "@/types/api";

interface MatchCardProps {
  match: Match;
  onClick?: () => void;
}

export function MatchCard({ match, onClick }: MatchCardProps) {
  const isActive = !match.result;

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (onClick && (e.key === "Enter" || e.key === " ")) {
      e.preventDefault();
      onClick();
    }
  };

  return (
    <Card
      className={cn(
        "transition-all",
        onClick && "cursor-pointer hover:border-valorant-red/50",
        isActive && "border-valorant-red/30"
      )}
      onClick={onClick}
      onKeyDown={handleKeyDown}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Swords className="h-4 w-4 text-valorant-red" />
            <span className="text-sm font-medium text-valorant-gray">
              {formatRankGroupShort(match.rank_group)}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {isActive ? (
              <Badge variant="warning">
                <Clock className="h-3 w-3 mr-1" />
                In Progress
              </Badge>
            ) : match.result === "cancelled" ? (
              <Badge variant="danger">Cancelled</Badge>
            ) : (
              <Badge variant="success">Completed</Badge>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <div className="flex items-center justify-between gap-4">
          {/* Red Team */}
          <div className="flex-1 text-center">
            <div
              className={cn(
                "text-lg font-bold",
                match.result === "red" && "text-valorant-red"
              )}
            >
              Red Team
            </div>
            <div className="text-sm text-valorant-gray">
              {match.players_red.length} players
            </div>
          </div>

          {/* Score */}
          <div className="flex flex-col items-center">
            <div className="text-2xl font-bold text-valorant-light">
              {formatScore(match.red_score, match.blue_score)}
            </div>
            {match.result && match.result !== "cancelled" && (
              <div className="flex items-center gap-1 mt-1">
                <Trophy className="h-3 w-3 text-valorant-gold" />
                <span
                  className={cn(
                    "text-xs font-medium",
                    match.result === "red" ? "text-red-400" : "text-blue-400"
                  )}
                >
                  {match.result === "red" ? "Red" : "Blue"} Wins
                </span>
              </div>
            )}
          </div>

          {/* Blue Team */}
          <div className="flex-1 text-center">
            <div
              className={cn(
                "text-lg font-bold",
                match.result === "blue" && "text-blue-400"
              )}
            >
              Blue Team
            </div>
            <div className="text-sm text-valorant-gray">
              {match.players_blue.length} players
            </div>
          </div>
        </div>

        {match.selected_map && (
          <div className="flex items-center justify-center gap-2 mt-4 text-sm text-valorant-gray">
            <MapPin className="h-4 w-4" />
            {match.selected_map}
          </div>
        )}

        <div className="text-center text-xs text-valorant-gray/50 mt-3">
          {formatRelativeTime(match.created_at)}
        </div>
      </CardContent>
    </Card>
  );
}
