export type RankGroup = 'iron-plat' | 'dia-asc' | 'imm-radiant'

export interface LeaderboardEntry {
  discord_id: string
  rank: string
  points: number
  matches_played: number
  winrate: number // 0–100
  streak: number
}

export interface Leaderboard {
  rank_group: RankGroup
  players: LeaderboardEntry[]
  last_updated: string // ISO
}

export interface Match {
  match_id: string
  players_red: string[]
  players_blue: string[]
  captain_red: string
  captain_blue: string
  lobby_master: string
  rank_group: RankGroup
  defense_start?: 'red' | 'blue'
  red_score?: number
  blue_score?: number
  result?: 'red' | 'blue' | 'cancelled'
  created_at: string // ISO
  ended_at?: string // ISO
}

export interface Player {
  discord_id: string
  riot_id: string
  rank?: string
  points: number
  matches_played: number
  wins: number
  losses: number
  winrate: number
}

export interface QueueEntry { discord_id: string }
export interface Queue { rank_group: RankGroup; players: QueueEntry[] }