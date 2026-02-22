import { api } from "./client";
import type { Queue, RankGroup } from "@/types/api";

export async function getAllQueues(): Promise<Record<string, Queue>> {
  const { data } = await api.get<{ queues: Record<string, Queue> }>("/queues");
  return data.queues;
}

export async function getQueue(rankGroup: RankGroup): Promise<Queue> {
  const { data } = await api.get<Queue>(`/queues/${rankGroup}`);
  return data;
}

export async function joinQueue(rankGroup: RankGroup): Promise<Queue> {
  const { data } = await api.post<Queue>(`/queues/${rankGroup}/join`);
  return data;
}

export async function leaveQueue(rankGroup: RankGroup): Promise<void> {
  await api.post(`/queues/${rankGroup}/leave`);
}

export async function getQueuePlayers(rankGroup: RankGroup): Promise<string[]> {
  const queue = await getQueue(rankGroup);
  return queue.players;
}
