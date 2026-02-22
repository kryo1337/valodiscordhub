import { QueueCard } from "./QueueCard";
import type { Queue, RankGroup } from "@/types/api";

interface QueueListProps {
  queues: Record<string, Queue>;
  userDiscordId?: string;
  onJoin: (rankGroup: RankGroup) => void;
  onLeave: (rankGroup: RankGroup) => void;
  loadingRankGroup?: RankGroup | null;
}

const RANK_GROUPS: RankGroup[] = ["iron-plat", "dia-asc", "imm-radiant"];

export function QueueList({
  queues,
  userDiscordId,
  onJoin,
  onLeave,
  loadingRankGroup,
}: QueueListProps) {
  return (
    <div className="grid gap-6 md:grid-cols-3">
      {RANK_GROUPS.map((rankGroup) => {
        const queue = queues[rankGroup];
        const isInQueue = userDiscordId
          ? queue?.players?.includes(userDiscordId)
          : false;

        return (
          <QueueCard
            key={rankGroup}
            queue={queue}
            rankGroup={rankGroup}
            isInQueue={isInQueue}
            onJoin={() => onJoin(rankGroup)}
            onLeave={() => onLeave(rankGroup)}
            isLoading={loadingRankGroup === rankGroup}
          />
        );
      })}
    </div>
  );
}
