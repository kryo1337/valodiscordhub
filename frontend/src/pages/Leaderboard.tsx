import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { leaderboardApi } from '../services/api'
import type { Leaderboard } from '../types'

const groups = [
  { id: 'iron-plat', label: 'Iron - Platinum' },
  { id: 'dia-asc', label: 'Diamond - Ascendant' },
  { id: 'imm-radiant', label: 'Immortal - Radiant' },
]

export default function LeaderboardPage() {
  const [group, setGroup] = useState('imm-radiant')
  const { data, isLoading, error } = useQuery<Leaderboard>({
    queryKey: ['leaderboard', group],
    queryFn: () => leaderboardApi.getLeaderboard(group),
    staleTime: 60_000,
  })

  return (
    <div className="max-w-6xl mx-auto p-4 text-white">
      <h1 className="text-2xl font-bold mb-4">Leaderboard</h1>
      <div className="mb-4">
        <select value={group} onChange={e => setGroup(e.target.value)} className="bg-gray-800 text-white px-3 py-2 rounded">
          {groups.map(g => <option key={g.id} value={g.id}>{g.label}</option>)}
        </select>
      </div>

      {isLoading && <div className="text-gray-300">Loading...</div>}
      {error && <div className="text-red-400">Failed to load leaderboard</div>}
      {data && (
        <div className="bg-gray-900 border border-gray-800 rounded overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-800">
              <tr>
                <th className="text-left px-3 py-2">#</th>
                <th className="text-left px-3 py-2">Player</th>
                <th className="text-left px-3 py-2">Rank</th>
                <th className="text-left px-3 py-2">Points</th>
                <th className="text-left px-3 py-2">Matches</th>
                <th className="text-left px-3 py-2">Winrate</th>
                <th className="text-left px-3 py-2">Streak</th>
              </tr>
            </thead>
            <tbody>
              {data.players.map((p, idx) => (
                <tr key={p.discord_id} className="odd:bg-gray-950">
                  <td className="px-3 py-2">{idx+1}</td>
                  <td className="px-3 py-2">{p.discord_id}</td>
                  <td className="px-3 py-2">{p.rank}</td>
                  <td className="px-3 py-2">{p.points}</td>
                  <td className="px-3 py-2">{p.matches_played}</td>
                  <td className="px-3 py-2">{p.winrate.toFixed(1)}%</td>
                  <td className="px-3 py-2">{p.streak}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}