import { Users, UserPlus, UserMinus } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent, CardFooter, Button } from "@/components/ui";
import { Avatar } from "@/components/common";
import { formatRankGroupShort } from "@/lib/format";
import type { Queue, RankGroup } from "@/types/api";

interface QueueCardProps {
  queue?: Queue;
  rankGroup: RankGroup;
  isInQueue: boolean;
  onJoin: () => void;
  onLeave: () => void;
  isLoading?: boolean;
}

export function QueueCard({
  queue,
  rankGroup,
  isInQueue,
  onJoin,
  onLeave,
  isLoading,
}: QueueCardProps) {
  const playerCount = queue?.players?.length || 0;
  const maxPlayers = 10;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5 text-valorant-red" />
            {formatRankGroupShort(rankGroup)}
          </CardTitle>
          <div className="flex items-center gap-2">
            <span
              className={`text-2xl font-bold ${
                playerCount >= maxPlayers ? "text-green-400" : "text-valorant-light"
              }`}
            >
              {playerCount}
            </span>
            <span className="text-valorant-gray">/ {maxPlayers}</span>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {playerCount > 0 ? (
          <div className="flex flex-wrap gap-2">
            {queue?.players?.map((playerId) => (
              <div
                key={playerId}
                className="flex items-center gap-2 bg-valorant-darker px-3 py-1.5 rounded-full"
              >
                <Avatar size="sm" fallback={playerId.slice(0, 2)} />
                <span className="text-sm text-valorant-light">
                  Player #{playerId.slice(-4)}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-valorant-gray">
            <Users className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p>No players in queue</p>
            <p className="text-sm">Be the first to join!</p>
          </div>
        )}
      </CardContent>

      <CardFooter>
        {isInQueue ? (
          <Button
            variant="danger"
            className="w-full"
            onClick={onLeave}
            isLoading={isLoading}
          >
            <UserMinus className="h-4 w-4 mr-2" />
            Leave Queue
          </Button>
        ) : (
          <Button
            className="w-full"
            onClick={onJoin}
            isLoading={isLoading}
            disabled={playerCount >= maxPlayers}
          >
            <UserPlus className="h-4 w-4 mr-2" />
            {playerCount >= maxPlayers ? "Queue Full" : "Join Queue"}
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
