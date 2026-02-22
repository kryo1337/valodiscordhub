import { api } from "./client";
import type { Player, LeaderboardEntry, RankGroup } from "@/types/api";

export async function getPlayer(discordId: string): Promise<Player> {
  const { data } = await api.get<Player>(`/players/${discordId}`);
  return data;
}

export async function getPlayerStats(discordId: string): Promise<Player> {
  const { data } = await api.get<Player>(`/players/${discordId}/stats`);
  return data;
}

export async function updatePlayer(
  discordId: string,
  updates: Partial<Player>
): Promise<Player> {
  const { data } = await api.patch<Player>(`/players/${discordId}`, updates);
  return data;
}

export async function getLeaderboard(
  rankGroup: RankGroup,
  limit = 50,
  offset = 0
): Promise<LeaderboardEntry[]> {
  const { data } = await api.get<{ entries: LeaderboardEntry[] }>(
    `/leaderboard/${rankGroup}?limit=${limit}&offset=${offset}`
  );
  return data.entries;
}

export async function searchPlayers(query: string): Promise<Player[]> {
  const { data } = await api.get<{ players: Player[] }>(
    `/players/search?q=${encodeURIComponent(query)}`
  );
  return data.players;
}
