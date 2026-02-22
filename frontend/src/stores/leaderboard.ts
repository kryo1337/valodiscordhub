import { create } from "zustand";
import { devtools } from "zustand/middleware";
import type { LeaderboardEntry, RankGroup } from "@/types/api";

interface LeaderboardState {
  entries: Record<string, LeaderboardEntry[]>;
  selectedRankGroup: RankGroup;
  loading: boolean;
  error: string | null;
  setEntries: (rankGroup: string, entries: LeaderboardEntry[]) => void;
  setSelectedRankGroup: (rankGroup: RankGroup) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useLeaderboardStore = create<LeaderboardState>()(
  devtools(
    (set) => ({
  entries: {},
  selectedRankGroup: "iron-plat",
  loading: false,
  error: null,
  setEntries: (rankGroup, entries) =>
    set((state) => ({
      entries: { ...state.entries, [rankGroup]: entries },
    })),
  setSelectedRankGroup: (selectedRankGroup) => set({ selectedRankGroup }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
}),
    { name: "LeaderboardStore" }
  )
);
