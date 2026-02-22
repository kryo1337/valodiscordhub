import { api } from "./client";
import type { Match, RankGroup } from "@/types/api";

export interface GetMatchesParams {
  rank_group?: RankGroup;
  active?: boolean;
  limit?: number;
  offset?: number;
}

export async function getMatches(
  params: GetMatchesParams = {}
): Promise<Match[]> {
  const searchParams = new URLSearchParams();
  if (params.rank_group) searchParams.append("rank_group", params.rank_group);
  if (params.active !== undefined)
    searchParams.append("active", String(params.active));
  if (params.limit) searchParams.append("limit", String(params.limit));
  if (params.offset) searchParams.append("offset", String(params.offset));

  const { data } = await api.get<{ matches: Match[] }>(
    `/matches?${searchParams.toString()}`
  );
  return data.matches;
}

export async function getMatch(matchId: string): Promise<Match> {
  const { data } = await api.get<Match>(`/matches/${matchId}`);
  return data;
}

export async function getActiveMatches(rankGroup?: RankGroup): Promise<Match[]> {
  return getMatches({ rank_group: rankGroup, active: true });
}

export async function submitScore(
  matchId: string,
  redScore: number,
  blueScore: number
): Promise<Match> {
  const { data } = await api.post<Match>(`/matches/${matchId}/score`, {
    red_score: redScore,
    blue_score: blueScore,
  });
  return data;
}

export async function cancelMatch(matchId: string): Promise<void> {
  await api.post(`/matches/${matchId}/cancel`);
}

export async function getMatchHistory(
  discordId?: string,
  limit = 20,
  offset = 0
): Promise<Match[]> {
  const searchParams = new URLSearchParams();
  if (discordId) searchParams.append("discord_id", discordId);
  searchParams.append("limit", String(limit));
  searchParams.append("offset", String(offset));
  searchParams.append("active", "false");

  const { data } = await api.get<{ matches: Match[] }>(
    `/matches?${searchParams.toString()}`
  );
  return data.matches;
}
