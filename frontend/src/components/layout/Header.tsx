import { NavLink } from 'react-router-dom'

export default function Header() {
  const link = 'text-gray-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium'
  const active = 'bg-gray-800 text-white'
  return (
    <header className="bg-gray-900 border-b border-gray-800">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
        <div className="text-white font-bold">ValoDiscordHub</div>
        <nav className="flex gap-2">
          <NavLink to="/" className={({isActive}) => `${link} ${isActive?active:''}`}>Home</NavLink>
          <NavLink to="/leaderboard" className={({isActive}) => `${link} ${isActive?active:''}`}>Leaderboard</NavLink>
          <NavLink to="/matches" className={({isActive}) => `${link} ${isActive?active:''}`}>Matches</NavLink>
        </nav>
      </div>
    </header>
  )
}