import { create } from "zustand";
import { devtools } from "zustand/middleware";
import type { Match } from "@/types/api";

interface MatchState {
  matches: Match[];
  activeMatches: Match[];
  currentMatch: Match | null;
  loading: boolean;
  error: string | null;
  setMatches: (matches: Match[]) => void;
  setActiveMatches: (matches: Match[]) => void;
  setCurrentMatch: (match: Match | null) => void;
  updateMatch: (matchId: string, updates: Partial<Match>) => void;
  addMatch: (match: Match) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useMatchStore = create<MatchState>()(
  devtools(
    (set) => ({
  matches: [],
  activeMatches: [],
  currentMatch: null,
  loading: false,
  error: null,
  setMatches: (matches) => set({ matches }),
  setActiveMatches: (activeMatches) => set({ activeMatches }),
  setCurrentMatch: (currentMatch) => set({ currentMatch }),
  updateMatch: (matchId, updates) =>
    set((state) => ({
      matches: state.matches.map((m) =>
        m.match_id === matchId ? { ...m, ...updates } : m
      ),
      activeMatches: state.activeMatches.map((m) =>
        m.match_id === matchId ? { ...m, ...updates } : m
      ),
      currentMatch:
        state.currentMatch?.match_id === matchId
          ? { ...state.currentMatch, ...updates }
          : state.currentMatch,
    })),
  addMatch: (match) =>
    set((state) => ({
      matches: [match, ...state.matches],
      activeMatches: match.result ? state.activeMatches : [match, ...state.activeMatches],
    })),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
}),
    { name: "MatchStore" }
  )
);
