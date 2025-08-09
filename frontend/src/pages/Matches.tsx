import { useQuery } from '@tanstack/react-query'
import { matchesApi } from '../services/api'
import type { Match } from '../types'

export default function MatchesPage() {
  const { data: active } = useQuery<Match[]>({
    queryKey: ['matches','active'],
    queryFn: matchesApi.getActiveMatches,
    staleTime: 30_000,
  })
  const { data: history, isLoading, error } = useQuery<Match[]>({
    queryKey: ['matches','history'],
    queryFn: () => matchesApi.getMatchHistory(20),
    staleTime: 60_000,
  })

  return (
    <div className="max-w-6xl mx-auto p-4 text-white">
      <h1 className="text-2xl font-bold mb-4">Matches</h1>

      <section className="mb-6">
        <h2 className="text-xl font-semibold mb-2">Active</h2>
        {!active?.length && <div className="text-gray-400">No active matches</div>}
        <ul className="space-y-2">
          {active?.map(m => (
            <li key={m.match_id} className="bg-gray-900 border border-gray-800 rounded p-3">
              <div className="text-sm text-gray-300">{m.match_id} • {m.rank_group}</div>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-2">Recent</h2>
        {isLoading && <div className="text-gray-300">Loading...</div>}
        {error && <div className="text-red-400">Failed to load match history</div>}
        <ul className="space-y-2">
          {history?.map(m => (
            <li key={m.match_id} className="bg-gray-900 border border-gray-800 rounded p-3">
              <div className="text-sm text-gray-300">{m.match_id} • {m.rank_group} • Result: {m.result ?? '—'}</div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}