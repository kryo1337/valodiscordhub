import { create } from "zustand";
import { devtools } from "zustand/middleware";
import type { Queue, RankGroup } from "@/types/api";

interface QueueState {
  queues: Record<string, Queue>;
  loading: boolean;
  error: string | null;
  setQueue: (rankGroup: string, queue: Queue) => void;
  setQueues: (queues: Record<string, Queue>) => void;
  updateQueuePlayers: (rankGroup: string, players: string[]) => void;
  addPlayerToQueue: (rankGroup: string, discordId: string) => void;
  removePlayerFromQueue: (rankGroup: string, discordId: string) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  isInQueue: (rankGroup: RankGroup, discordId: string) => boolean;
}

export const useQueueStore = create<QueueState>()(
  devtools(
    (set, get) => ({
  queues: {},
  loading: false,
  error: null,
  setQueue: (rankGroup, queue) =>
    set((state) => ({
      queues: { ...state.queues, [rankGroup]: queue },
    })),
  setQueues: (queues) => set({ queues }),
  updateQueuePlayers: (rankGroup, players) =>
    set((state) => ({
      queues: {
        ...state.queues,
        [rankGroup]: {
          ...state.queues[rankGroup],
          players,
        },
      },
    })),
  addPlayerToQueue: (rankGroup, discordId) =>
    set((state) => ({
      queues: {
        ...state.queues,
        [rankGroup]: {
          ...state.queues[rankGroup],
          players: [...(state.queues[rankGroup]?.players || []), discordId],
        },
      },
    })),
  removePlayerFromQueue: (rankGroup, discordId) =>
    set((state) => ({
      queues: {
        ...state.queues,
        [rankGroup]: {
          ...state.queues[rankGroup],
          players: state.queues[rankGroup]?.players.filter((id) => id !== discordId) || [],
        },
      },
    })),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  isInQueue: (rankGroup, discordId) => {
    const queue = get().queues[rankGroup];
    return queue?.players?.includes(discordId) ?? false;
  },
}),
    { name: "QueueStore" }
  )
);
