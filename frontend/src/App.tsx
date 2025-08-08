import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

const queryClient = new QueryClient()

const Home = () => (
  <div className="min-h-screen bg-gray-900 text-white p-4">
    <div className="max-w-4xl mx-auto">
      <h1 className="text-4xl font-bold mb-4">ValoDiscordHub</h1>
      <p className="text-gray-300">Welcome to the Valorant Discord Hub</p>
    </div>
  </div>
)

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
