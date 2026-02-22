import { useEffect, useState } from "react";
import { useAuth } from "@/hooks";
import { useQueueStore } from "@/stores";
import { queueApi } from "@/api";
import { QueueList } from "@/components/queue";
import { LoadingPage, ErrorMessage } from "@/components/common";
import { getErrorMessage } from "@/lib/errors";
import type { RankGroup } from "@/types/api";

export default function Queue() {
  const { user } = useAuth();
  const { queues, setQueues, setLoading, loading, error, setError, addPlayerToQueue, removePlayerFromQueue } = useQueueStore();
  const [loadingRankGroup, setLoadingRankGroup] = useState<RankGroup | null>(null);

  useEffect(() => {
    const fetchQueues = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await queueApi.getAllQueues();
        setQueues(data);
      } catch (e) {
        console.error("Failed to fetch queues:", e);
        setError("Failed to load queues. Please try again.");
      } finally {
        setLoading(false);
      }
    };
    fetchQueues();
  }, [setQueues, setLoading, setError]);

  const handleJoin = async (rankGroup: RankGroup) => {
    if (!user?.discord_id) return;

    const isInQueue = queues[rankGroup]?.players?.includes(user.discord_id);
    if (isInQueue) return; // Already in queue

    setLoadingRankGroup(rankGroup);

    // Optimistic update: add user immediately
    const prevQueue = queues[rankGroup];
    addPlayerToQueue(rankGroup, user.discord_id);

    try {
      const queue = await queueApi.joinQueue(rankGroup);
      setQueues({ ...queues, [rankGroup]: queue });
    } catch (e: unknown) {
      console.error("Failed to join queue:", e);
      // Rollback optimistic update
      setQueues({ ...queues, [rankGroup]: prevQueue });
      setError(getErrorMessage(e));
    } finally {
      setLoadingRankGroup(null);
    }
  };

  const handleLeave = async (rankGroup: RankGroup) => {
    if (!user?.discord_id) return;

    const isInQueue = queues[rankGroup]?.players?.includes(user.discord_id);
    if (!isInQueue) return; // Not in queue

    setLoadingRankGroup(rankGroup);

    // Optimistic update: remove user immediately
    const prevQueue = queues[rankGroup];
    removePlayerFromQueue(rankGroup, user.discord_id);

    try {
      await queueApi.leaveQueue(rankGroup);
      // Fetch fresh state to confirm
      const data = await queueApi.getAllQueues();
      setQueues(data);
    } catch (e: unknown) {
      console.error("Failed to leave queue:", e);
      // Rollback optimistic update
      setQueues({ ...queues, [rankGroup]: prevQueue });
      setError(getErrorMessage(e));
    } finally {
      setLoadingRankGroup(null);
    }
  };

  if (loading && Object.keys(queues).length === 0) {
    return <LoadingPage />;
  }

  if (error && Object.keys(queues).length === 0) {
    return (
      <ErrorMessage
        title="Failed to load queues"
        message={error}
        onRetry={() => window.location.reload()}
      />
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-valorant-light">Queue</h1>
        <p className="text-valorant-gray mt-2">
          Join a queue for your rank group and wait for a match
        </p>
      </div>

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400">
          {error}
        </div>
      )}

      <QueueList
        queues={queues}
        userDiscordId={user?.discord_id}
        onJoin={handleJoin}
        onLeave={handleLeave}
        loadingRankGroup={loadingRankGroup}
      />
    </div>
  );
}
