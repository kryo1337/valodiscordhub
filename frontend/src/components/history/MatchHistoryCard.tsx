import { Clock, MapPin, Trophy, XCircle } from "lucide-react";
import { Card, CardContent, Badge } from "@/components/ui";
import { formatDateTime, formatRankGroupShort } from "@/lib/format";
import { cn } from "@/lib/cn";
import type { Match } from "@/types/api";

interface MatchHistoryCardProps {
  match: Match;
  userDiscordId?: string;
}

export function MatchHistoryCard({ match, userDiscordId }: MatchHistoryCardProps) {
  const userTeam = userDiscordId
    ? match.players_red.includes(userDiscordId)
      ? "red"
      : match.players_blue.includes(userDiscordId)
      ? "blue"
      : null
    : null;

  const isWin = userTeam === match.result;
  const isLoss = userTeam && userTeam !== match.result && match.result !== "cancelled";

  return (
    <Card
      className={cn(
        "transition-all",
        isWin && "border-l-4 border-l-green-500",
        isLoss && "border-l-4 border-l-red-500",
        match.result === "cancelled" && "opacity-60"
      )}
    >
      <CardContent className="py-4">
        <div className="flex items-center justify-between gap-4">
          {/* Left: Match info */}
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <Badge variant={isWin ? "success" : isLoss ? "danger" : "default"}>
                {match.result === "cancelled" ? (
                  <>
                    <XCircle className="h-3 w-3 mr-1" />
                    Cancelled
                  </>
                ) : isWin ? (
                  <>
                    <Trophy className="h-3 w-3 mr-1" />
                    Victory
                  </>
                ) : isLoss ? (
                  "Defeat"
                ) : (
                  match.result === "red" ? "Red Won" : "Blue Won"
                )}
              </Badge>
              <span className="text-xs text-valorant-gray">
                {formatRankGroupShort(match.rank_group)}
              </span>
            </div>

            <div className="flex items-center gap-4 text-sm text-valorant-gray">
              {match.selected_map && (
                <div className="flex items-center gap-1">
                  <MapPin className="h-3 w-3" />
                  {match.selected_map}
                </div>
              )}
              <div className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {formatDateTime(match.created_at)}
              </div>
            </div>
          </div>

          {/* Right: Score */}
          <div className="text-center">
            <div className="text-2xl font-bold">
              <span
                className={cn(
                  userTeam === "red" ? "text-valorant-light" : "text-valorant-gray"
                )}
              >
                {match.red_score ?? "-"}
              </span>
              <span className="text-valorant-gray/50 mx-2">:</span>
              <span
                className={cn(
                  userTeam === "blue" ? "text-valorant-light" : "text-valorant-gray"
                )}
              >
                {match.blue_score ?? "-"}
              </span>
            </div>
            {userTeam && (
              <div
                className={cn(
                  "text-xs mt-1",
                  userTeam === "red" ? "text-red-400" : "text-blue-400"
                )}
              >
                {userTeam === "red" ? "Red Team" : "Blue Team"}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
