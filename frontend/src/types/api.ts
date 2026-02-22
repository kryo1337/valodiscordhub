export interface Player {
  discord_id: string;
  riot_id: string;
  rank: string;
  points: number;
  matches_played: number;
  wins: number;
  losses: number;
  winrate: number;
  display_name?: string;
  avatar_url?: string;
}

export interface Match {
  match_id: string;
  players_red: string[];
  players_blue: string[];
  captain_red: string;
  captain_blue: string;
  lobby_master: string;
  rank_group: RankGroup;
  defense_start: "red" | "blue" | null;
  banned_maps: string[];
  selected_map: string | null;
  red_score: number | null;
  blue_score: number | null;
  result: MatchResult | null;
  created_at: string;
  ended_at: string | null;
}

export interface Queue {
  rank_group: string;
  players: string[];
  created_at: string;
}

export interface LeaderboardEntry {
  rank: number;
  discord_id: string;
  riot_id: string;
  rank_val: string;
  points: number;
  wins: number;
  losses: number;
  winrate: number;
  display_name?: string;
  avatar_url?: string;
}

export interface AuthResponse {
  jwt: string;
  user: User;
}

export interface User {
  id: string;
  discord_id: string;
  username: string;
  email: string;
  avatar: string;
}

export interface ApiError {
  error: boolean;
  message: string;
  details?: unknown;
}

export type RankGroup = "iron-plat" | "dia-asc" | "imm-radiant";
export type MatchResult = "red" | "blue" | "cancelled";

export interface QueueResponse {
  queues: Record<string, Queue>;
}

export interface MatchListResponse {
  matches: Match[];
  total: number;
}

export interface LeaderboardResponse {
  entries: LeaderboardEntry[];
  rank_group: string;
  total: number;
}
