import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Header from './components/layout/Header'
import LeaderboardPage from './pages/Leaderboard'
import MatchesPage from './pages/Matches'

const queryClient = new QueryClient()

const Home = () => (
  <div className="max-w-6xl mx-auto p-4 text-white">
    <h1 className="text-3xl font-bold">ValoDiscordHub</h1>
    <p className="text-gray-300">Welcome to the Valorant Discord Hub</p>
  </div>
)

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-gray-950">
        <BrowserRouter>
          <Header />
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/leaderboard" element={<LeaderboardPage />} />
            <Route path="/matches" element={<MatchesPage />} />
          </Routes>
        </BrowserRouter>
      </div>
    </QueryClientProvider>
  )
}
