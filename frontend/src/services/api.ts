import axios from 'axios'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
})

export const leaderboardApi = {
  getLeaderboard: (rankGroup: string) => api.get<any>(`/leaderboard/${rankGroup}`).then(res => res.data),
}

export const matchesApi = {
  getMatchHistory: (limit = 10) => api.get<any[]>(
    '/matches/history', { params: { limit } }
  ).then(res => res.data),
  getActiveMatches: () => api.get<any[]>(
    '/matches/active'
  ).then(res => res.data),
  getMatch: (matchId: string) => api.get<any>(
    `/matches/${matchId}`
  ).then(res => res.data),
}

export const playersApi = {
  listPlayers: (skip = 0, limit = 10) => api.get<any[]>(
    '/players', { params: { skip, limit } }
  ).then(res => res.data),
  getPlayer: (discordId: string) => api.get<any>(
    `/players/${discordId}`
  ).then(res => res.data),
}

export const preferencesApi = {
  getUserPreferences: (discordId: string) => api.get<any>(
    `/preferences/${discordId}`
  ).then(res => res.data),
}

export const queueApi = {
  getQueue: (rankGroup: string) => api.get<any>(
    `/queue/${rankGroup}`
  ).then(res => res.data),
}