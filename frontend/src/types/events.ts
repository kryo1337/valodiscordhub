import type { LeaderboardEntry } from "./api";

export type EventType =
  | "queue_update"
  | "match_created"
  | "match_updated"
  | "match_result"
  | "leaderboard_update"
  | "player_updated";

export interface BaseEvent {
  type: EventType;
  timestamp: string;
}

export interface QueueUpdateEvent extends BaseEvent {
  type: "queue_update";
  rank_group: string;
  action: "joined" | "left" | "cleared";
  discord_id?: string;
  queue_count: number;
  players: string[];
}

export interface MatchCreatedEvent extends BaseEvent {
  type: "match_created";
  match_id: string;
  rank_group: string;
  players_red: string[];
  players_blue: string[];
  captain_red: string;
  captain_blue: string;
}

export interface MatchUpdatedEvent extends BaseEvent {
  type: "match_updated";
  match_id: string;
  update_type: "teams" | "captains" | "draft" | "score" | "cancelled";
  data: Record<string, unknown>;
}

export interface MatchResultEvent extends BaseEvent {
  type: "match_result";
  match_id: string;
  result: "red" | "blue" | "cancelled";
  red_score?: number;
  blue_score?: number;
}

export interface LeaderboardUpdateEvent extends BaseEvent {
  type: "leaderboard_update";
  rank_group: string;
  top_players: LeaderboardEntry[];
}

export interface PlayerUpdatedEvent extends BaseEvent {
  type: "player_updated";
  discord_id: string;
  field: "rank" | "points" | "riot_id";
  value: string;
}

export type WebSocketEvent =
  | QueueUpdateEvent
  | MatchCreatedEvent
  | MatchUpdatedEvent
  | MatchResultEvent
  | LeaderboardUpdateEvent
  | PlayerUpdatedEvent;
