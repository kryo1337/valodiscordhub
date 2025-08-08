# Frontend Implementation Guide for ValoDiscordHub

## 1. Overview

This guide outlines how to implement a React + Tailwind CSS frontend for the ValoDiscordHub API. The frontend will provide a modern web interface for users to view leaderboards, match history, player stats, and manage their preferences, with Discord OAuth2 authentication.

---

## 2. Frontend Architecture

**Directory structure suggestion:**

```
frontend/
  public/
    index.html
    favicon.ico
  src/
    components/
      auth/
        LoginButton.tsx
        UserProfile.tsx
      layout/
        Header.tsx
        Sidebar.tsx
        Footer.tsx
      leaderboard/
        LeaderboardTable.tsx
        RankGroupSelector.tsx
        Pagination.tsx
      matches/
        MatchHistory.tsx
        MatchCard.tsx
        MatchDetails.tsx
      players/
        PlayerStats.tsx
        PlayerSearch.tsx
        PlayerCard.tsx
      queue/
        QueueStatus.tsx
        QueueButton.tsx
      common/
        LoadingSpinner.tsx
        ErrorBoundary.tsx
        Modal.tsx
    pages/
      Home.tsx
      Leaderboard.tsx
      MatchHistory.tsx
      PlayerStats.tsx
      Profile.tsx
      Admin.tsx
    hooks/
      useAuth.ts
      useApi.ts
      useLocalStorage.ts
    services/
      api.ts
      auth.ts
    types/
      index.ts
    utils/
      constants.ts
      helpers.ts
    styles/
      globals.css
    App.tsx
    index.tsx
  package.json
  tailwind.config.js
  tsconfig.json
  vite.config.ts
```

**Key technologies:**
- **React 18** with TypeScript
- **Vite** for fast development and building
- **Tailwind CSS** for styling
- **React Router** for navigation
- **React Query/TanStack Query** for API state management
- **Axios** for HTTP requests
- **React Hook Form** for form handling
- **Lucide React** for icons

---

## 3. Authentication Flow

### 3.1 Discord OAuth2 Integration

**Implementation steps:**
1. **Login Button Component:**
   ```tsx
   const LoginButton = () => {
     const handleLogin = () => {
       window.location.href = `${API_BASE_URL}/auth/login`;
     };
     
     return (
       <button 
         onClick={handleLogin}
         className="bg-[#5865F2] hover:bg-[#4752C4] text-white px-6 py-2 rounded-lg flex items-center gap-2"
       >
         <DiscordIcon className="w-5 h-5" />
         Login with Discord
       </button>
     );
   };
   ```

2. **OAuth Callback Handler:**
   ```tsx
   // In App.tsx or dedicated callback component
   useEffect(() => {
     const urlParams = new URLSearchParams(window.location.search);
     const code = urlParams.get('code');
     
     if (code) {
       // Exchange code for JWT
       exchangeCodeForToken(code);
     }
   }, []);
   ```

3. **JWT Management:**
   - Store JWT in localStorage or httpOnly cookies
   - Implement automatic token refresh
   - Handle token expiration gracefully

### 3.2 Protected Routes

```tsx
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated, isLoading } = useAuth();
  
  if (isLoading) return <LoadingSpinner />;
  if (!isAuthenticated) return <Navigate to="/login" />;
  
  return <>{children}</>;
};
```

---

## 4. Core Components

### 4.1 Layout Components

**Header Component:**
```tsx
const Header = () => {
  const { user, logout } = useAuth();
  
  return (
    <header className="bg-gray-900 text-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center">
            <img src="/logo.png" alt="ValoDiscordHub" className="h-8 w-8" />
            <span className="ml-2 text-xl font-bold">ValoDiscordHub</span>
          </div>
          
          <nav className="hidden md:flex space-x-8">
            <NavLink to="/" className="hover:text-blue-400">Home</NavLink>
            <NavLink to="/leaderboard" className="hover:text-blue-400">Leaderboard</NavLink>
            <NavLink to="/matches" className="hover:text-blue-400">Matches</NavLink>
            <NavLink to="/stats" className="hover:text-blue-400">Stats</NavLink>
          </nav>
          
          <div className="flex items-center space-x-4">
            {user ? (
              <UserProfile user={user} onLogout={logout} />
            ) : (
              <LoginButton />
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
```

### 4.2 Leaderboard Components

**Leaderboard Table:**
```tsx
const LeaderboardTable = ({ rankGroup }: { rankGroup: string }) => {
  const { data: leaderboard, isLoading, error } = useQuery({
    queryKey: ['leaderboard', rankGroup],
    queryFn: () => api.get(`/leaderboard/${rankGroup}`)
  });
  
  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;
  
  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Rank
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Player
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Points
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Matches
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Winrate
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Streak
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {leaderboard.players.map((player, index) => (
            <LeaderboardRow 
              key={player.discord_id} 
              player={player} 
              rank={index + 1} 
            />
          ))}
        </tbody>
      </table>
    </div>
  );
};
```

### 4.3 Match History Components

**Match Card:**
```tsx
const MatchCard = ({ match }: { match: Match }) => {
  const isRedWinner = match.result === 'red';
  const isBlueWinner = match.result === 'blue';
  
  return (
    <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
      <div className="flex justify-between items-start mb-4">
        <h3 className="text-lg font-semibold text-gray-900">
          Match {match.match_id}
        </h3>
        <span className={`px-2 py-1 rounded text-xs font-medium ${
          match.result === 'cancelled' 
            ? 'bg-gray-100 text-gray-800'
            : 'bg-green-100 text-green-800'
        }`}>
          {match.result === 'cancelled' ? 'Cancelled' : 'Completed'}
        </span>
      </div>
      
      <div className="grid grid-cols-2 gap-4">
        <div className={`p-4 rounded-lg ${
          isRedWinner ? 'bg-red-50 border-2 border-red-200' : 'bg-gray-50'
        }`}>
          <h4 className="font-medium text-gray-900 mb-2">🔴 Red Team</h4>
          <div className="space-y-1">
            {match.players_red.map((playerId, index) => (
              <div key={playerId} className="flex items-center">
                {index === 0 && <CrownIcon className="w-4 h-4 text-yellow-500 mr-1" />}
                <span className="text-sm">{playerId}</span>
              </div>
            ))}
          </div>
          {match.red_score !== null && (
            <div className="mt-2 text-lg font-bold text-red-600">
              {match.red_score}
            </div>
          )}
        </div>
        
        <div className={`p-4 rounded-lg ${
          isBlueWinner ? 'bg-blue-50 border-2 border-blue-200' : 'bg-gray-50'
        }`}>
          <h4 className="font-medium text-gray-900 mb-2">🔵 Blue Team</h4>
          <div className="space-y-1">
            {match.players_blue.map((playerId, index) => (
              <div key={playerId} className="flex items-center">
                {index === 0 && <CrownIcon className="w-4 h-4 text-yellow-500 mr-1" />}
                <span className="text-sm">{playerId}</span>
              </div>
            ))}
          </div>
          {match.blue_score !== null && (
            <div className="mt-2 text-lg font-bold text-blue-600">
              {match.blue_score}
            </div>
          )}
        </div>
      </div>
      
      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="flex justify-between text-sm text-gray-600">
          <span>Duration: {formatDuration(match.duration)}</span>
          <span>Created: {formatDate(match.created_at)}</span>
        </div>
      </div>
    </div>
  );
};
```

---

## 5. API Integration

### 5.1 API Service Layer

```tsx
// services/api.ts
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

// Public, read-only endpoints that the frontend is allowed to call
export const leaderboardApi = {
  getLeaderboard: (rankGroup: string) =>
    api.get(`/leaderboard/${rankGroup}`).then(res => res.data),
  // Note: backend does not support server-side pagination params
};

export const matchesApi = {
  getMatchHistory: (limit?: number) =>
    api.get('/matches/history', { params: { limit } }).then(res => res.data),
  getActiveMatches: () => api.get('/matches/active').then(res => res.data),
  getMatch: (matchId: string) => api.get(`/matches/${matchId}`).then(res => res.data),
};

export const playersApi = {
  // List players with skip/limit (no search endpoint in backend)
  listPlayers: (skip = 0, limit = 10) =>
    api.get('/players', { params: { skip, limit } }).then(res => res.data),
  getPlayer: (discordId: string) => api.get(`/players/${discordId}`).then(res => res.data),
};

export const preferencesApi = {
  getUserPreferences: (discordId: string) =>
    api.get(`/preferences/${discordId}`).then(res => res.data),
  // Note: PATCH /preferences/{discord_id} requires Bot token in backend. Frontend should not call protected endpoints.
};

export const queueApi = {
  // Read-only queue view (join/leave require bot token → not for frontend)
  getQueue: (rankGroup: string) => api.get(`/queue/${rankGroup}`).then(res => res.data),
};
```

### 5.2 React Query Integration

```tsx
// hooks/useApi.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { leaderboardApi, matchesApi, playersApi, preferencesApi } from '../services/api';

export const useLeaderboard = (rankGroup: string) => {
  return useQuery({
    queryKey: ['leaderboard', rankGroup],
    queryFn: () => leaderboardApi.getLeaderboard(rankGroup),
    staleTime: 30000, // 30 seconds
  });
};

export const useMatchHistory = (limit?: number) => {
  return useQuery({
    queryKey: ['matchHistory', limit],
    queryFn: () => matchesApi.getMatchHistory(limit),
    staleTime: 60000, // 1 minute
  });
};

export const usePlayer = (discordId: string) => {
  return useQuery({
    queryKey: ['player', discordId],
    queryFn: () => playersApi.getPlayer(discordId),
    enabled: !!discordId,
  });
};

export const useUpdatePreferences = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ discordId, preferences }: { discordId: string; preferences: Partial<UserPreferences> }) =>
      preferencesApi.updateUserPreferences(discordId, preferences),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries(['preferences', variables.discordId]);
    },
  });
};
```

---

## 6. State Management

### 6.1 Authentication Context

```tsx
// hooks/useAuth.ts
import { createContext, useContext, useState, useEffect } from 'react';
import jwtDecode from 'jwt-decode';

type JwtPayload = { discord_id: string; username: string; email?: string };

interface User { discord_id: string; username: string; email?: string }
interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (jwt: string, userPayload?: User) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('jwt_token');
    if (token) {
      try {
        const decoded = jwtDecode<JwtPayload>(token);
        setUser({ discord_id: decoded.discord_id, username: decoded.username, email: decoded.email });
      } catch {
        localStorage.removeItem('jwt_token');
      }
    }
    setIsLoading(false);
  }, []);

  const login = (jwt: string, payload?: User) => {
    localStorage.setItem('jwt_token', jwt);
    if (payload) {
      setUser(payload);
    } else {
      try {
        const decoded = jwtDecode<JwtPayload>(jwt);
        setUser({ discord_id: decoded.discord_id, username: decoded.username, email: decoded.email });
      } catch {
        localStorage.removeItem('jwt_token');
      }
    }
  };

  const logout = () => {
    localStorage.removeItem('jwt_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
};
```

---

## 7. Styling with Tailwind CSS

### 7.1 Custom Configuration

```js
// tailwind.config.js
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'valorant-red': '#FF4655',
        'valorant-blue': '#0F1419',
        'valorant-gold': '#FFD700',
        'discord-blurple': '#5865F2',
      },
      fontFamily: {
        'valorant': ['DIN Next LT Pro', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
};
```

### 7.2 Component Styling Examples

**Gradient Backgrounds:**
```tsx
<div className="bg-gradient-to-br from-valorant-blue via-gray-900 to-black min-h-screen">
```

**Card Styling:**
```tsx
<div className="bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl p-6 shadow-xl">
```

**Button Variants:**
```tsx
const Button = ({ variant = 'primary', children, ...props }) => {
  const baseClasses = "px-4 py-2 rounded-lg font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2";
  
  const variants = {
    primary: "bg-valorant-red hover:bg-red-600 text-white focus:ring-red-500",
    secondary: "bg-gray-600 hover:bg-gray-700 text-white focus:ring-gray-500",
    outline: "border-2 border-valorant-red text-valorant-red hover:bg-valorant-red hover:text-white",
  };
  
  return (
    <button className={`${baseClasses} ${variants[variant]}`} {...props}>
      {children}
    </button>
  );
};
```

---

## 8. Responsive Design

### 8.1 Mobile-First Approach

```tsx
const ResponsiveLayout = ({ children }: { children: React.ReactNode }) => {
  return (
    <div className="min-h-screen bg-gray-900">
      {/* Mobile Header */}
      <header className="md:hidden bg-gray-800 p-4">
        <MobileMenu />
      </header>
      
      {/* Desktop Header */}
      <header className="hidden md:block">
        <DesktopHeader />
      </header>
      
      {/* Main Content */}
      <main className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Sidebar - hidden on mobile */}
          <aside className="hidden lg:block">
            <Sidebar />
          </aside>
          
          {/* Main content area */}
          <div className="lg:col-span-3">
            {children}
          </div>
        </div>
      </main>
    </div>
  );
};
```

### 8.2 Responsive Tables

```tsx
const ResponsiveTable = ({ data }: { data: any[] }) => {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        {/* Table content */}
      </table>
    </div>
  );
};
```

---

## 9. Performance Optimization

### 9.1 Code Splitting

```tsx
// App.tsx
import { lazy, Suspense } from 'react';

const Leaderboard = lazy(() => import('./pages/Leaderboard'));
const MatchHistory = lazy(() => import('./pages/MatchHistory'));
const PlayerStats = lazy(() => import('./pages/PlayerStats'));

function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <Routes>
        <Route path="/leaderboard" element={<Leaderboard />} />
        <Route path="/matches" element={<MatchHistory />} />
        <Route path="/stats" element={<PlayerStats />} />
      </Routes>
    </Suspense>
  );
}
```

### 9.2 Image Optimization

```tsx
// components/PlayerAvatar.tsx
import { useState } from 'react';

const PlayerAvatar = ({ discordId, size = 'md' }: { discordId: string; size?: 'sm' | 'md' | 'lg' }) => {
  const [imageError, setImageError] = useState(false);
  
  const sizes = {
    sm: 'w-8 h-8',
    md: 'w-12 h-12',
    lg: 'w-16 h-16',
  };
  
  if (imageError) {
    return (
      <div className={`${sizes[size]} bg-gray-300 rounded-full flex items-center justify-center`}>
        <UserIcon className="w-1/2 h-1/2 text-gray-600" />
      </div>
    );
  }
  
  return (
    <img
      src={`https://cdn.discordapp.com/avatars/${discordId}/${discordId}.png`}
      alt="Player avatar"
      className={`${sizes[size]} rounded-full object-cover`}
      onError={() => setImageError(true)}
      loading="lazy"
    />
  );
};
```

---

## 10. Error Handling

### 10.1 Error Boundaries

```tsx
// components/ErrorBoundary.tsx
import { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-900">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-white mb-4">
              Something went wrong
            </h1>
            <button
              onClick={() => window.location.reload()}
              className="bg-valorant-red hover:bg-red-600 text-white px-4 py-2 rounded"
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
```

### 10.2 API Error Handling

```tsx
// components/ErrorMessage.tsx
const ErrorMessage = ({ error }: { error: any }) => {
  const getErrorMessage = (error: any) => {
    if (error.response?.data?.detail) {
      return error.response.data.detail;
    }
    if (error.message) {
      return error.message;
    }
    return 'An unexpected error occurred';
  };

  return (
    <div className="bg-red-50 border border-red-200 rounded-md p-4">
      <div className="flex">
        <ExclamationTriangleIcon className="h-5 w-5 text-red-400" />
        <div className="ml-3">
          <h3 className="text-sm font-medium text-red-800">
            Error
          </h3>
          <div className="mt-2 text-sm text-red-700">
            {getErrorMessage(error)}
          </div>
        </div>
      </div>
    </div>
  );
};
```

---

## 11. Testing Strategy

### 11.1 Unit Tests

```tsx
// __tests__/components/LeaderboardTable.test.tsx
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { LeaderboardTable } from '../../components/leaderboard/LeaderboardTable';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
  },
});

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={queryClient}>
    {children}
  </QueryClientProvider>
);

test('renders leaderboard table', () => {
  render(<LeaderboardTable rankGroup="imm-radiant" />, { wrapper });
  expect(screen.getByText('Rank')).toBeInTheDocument();
});
```

### 11.2 Integration Tests

```tsx
// __tests__/pages/Leaderboard.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Leaderboard from '../../pages/Leaderboard';

test('loads and displays leaderboard data', async () => {
  render(
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <Leaderboard />
      </QueryClientProvider>
    </BrowserRouter>
  );

  await waitFor(() => {
    expect(screen.getByText('Leaderboard')).toBeInTheDocument();
  });
});
```

---

## 12. Deployment

### 12.1 Build Configuration

```js
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          router: ['react-router-dom'],
          query: ['@tanstack/react-query'],
        },
      },
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
});
```

### 12.2 Environment Variables

```env
# .env.production
VITE_API_BASE_URL=https://api.valodiscordhub.com
VITE_DISCORD_CLIENT_ID=your_discord_client_id
VITE_APP_NAME=ValoDiscordHub
```

---

## 13. Implementation Checklist

- [ ] Set up React + TypeScript + Vite project
- [ ] Configure Tailwind CSS and custom theme
- [ ] Set up React Router for navigation
- [ ] Implement Discord OAuth2 authentication flow
- [ ] Create API service layer with axios
- [ ] Set up React Query for state management
- [ ] Implement authentication context and protected routes
- [ ] Create responsive layout components (Header, Sidebar, Footer)
- [ ] Build leaderboard page with filtering and pagination
- [ ] Build match history page with detailed match cards
- [ ] Build player stats page with search functionality
- [ ] Build user profile page with preferences management
- [ ] Implement error boundaries and loading states
- [ ] Add responsive design for mobile devices
- [ ] Set up unit and integration tests
- [ ] Configure build and deployment pipeline
- [ ] Add performance optimizations (code splitting, lazy loading)
- [ ] Implement proper error handling and user feedback
- [ ] Add accessibility features (ARIA labels, keyboard navigation)
- [ ] Set up monitoring and analytics

---

## 14. Notes for Future AI Work

- Use this file as a reference for frontend architecture, component design, and implementation patterns.
- Follow the established API structure from the backend for consistent data flow.
- Prioritize user experience with smooth animations, loading states, and error handling.
- Ensure responsive design works across all device sizes.
- Implement proper TypeScript types for all API responses and component props.
- Use React Query for efficient caching and state management.
- Follow Tailwind CSS best practices for maintainable styling.
- Test thoroughly across different browsers and devices.
- Consider implementing PWA features for better mobile experience.
- Monitor performance and optimize bundle size regularly. 

## 15. Production Considerations (50k+ Discord users)

### 15.1 API usage patterns
- Prefer read-heavy, write-light flows from the public web. All mutations happen via the bot with Bot token.
- Cache aggressively in the client (React Query):
  - Leaderboards: staleTime 60–120s, background refetch on window focus
  - Match history: staleTime 30–60s, paginate client-side by requesting `limit` chunks
  - Queues: treat as near-real-time but poll at modest interval (10–20s) to avoid hammering the API
- Implement exponential backoff on network errors; surface soft errors (toasts) instead of blocking UI.

### 15.2 Pagination and data shaping
- Backend returns full leaderboard by rank group. For large lists, implement client-side pagination and virtualization (e.g., react-virtualized/react-window) to keep DOM light.
- For match history, use the `limit` param and an infinite-scroll pattern (append-only) with `useInfiniteQuery`.

### 15.3 Performance & Delivery
- Use Vite code-splitting; ensure largest page bundles < 200KB gzipped.
- Preload critical routes (leaderboard, home) and lazy load admin views.
- Image optimization: avatars with width/height, lazy loading, fallback placeholders.
- Measure with Lighthouse and Web Vitals; set a budget (LCP < 2.5s on 4G).

### 15.4 Security
- Never store the Bot token in the frontend; only the backend uses it.
- Store JWT in localStorage (fast path) or switch to httpOnly cookies if you need stronger CSRF guarantees. If using localStorage, protect sensitive calls server-side.
- Validate/guard all user-visible IDs (e.g., Discord IDs) before rendering.

### 15.5 Observability
- Add client-side analytics for navigation and API error rates (e.g., Plausible/Umami/Sentry):
  - Track API failures per route (leaderboard, matches, players)
  - Track slow endpoints (> 1s) to surface backend regressions
- Configure Sentry (or similar) for error reporting with release tags.

### 15.6 UX at scale
- Use skeletons and optimistic UI where harmless (e.g., pagination switches) to reduce perceived latency.
- Add an in-app status banner if API is degraded (based on a simple `/healthz` fetch).
- Provide a compact mode for tables; keep row heights small for large datasets.

### 15.7 Internationalization & Accessibility
- Wrap copy in an i18n layer (even if EN-only to start) to ease future locale support.
- Ensure keyboard navigation and ARIA labels on all interactive components (table pagers, dropdowns, modals).

### 15.8 Deployment & CDN
- Serve static assets via a CDN; set far-future cache headers with content hashing.
- Configure a simple `/healthz` check for the frontend hosting (if applicable) and monitor uptime.

### 15.9 Rate Limiting and Backoff (UI)
- On 429/5xx responses, back off requests (e.g., +2s, +4s, max 30s) and display a non-blocking banner.
- Avoid concurrent refetch storms: use React Query’s deduping and disable refetchOnWindowFocus for rapidly changing pages (like queue) if it causes churn.

### 15.10 Admin-only views
- Do not expose bot-protected operations in the web UI. If you later add a web admin, create a separate backend surface with proper auth and scopes.

---

## 16. Concrete Types from Backend (for frontend typing)

```ts
// types/index.ts (derive from backend models)
export type RankGroup = 'iron-plat' | 'dia-asc' | 'imm-radiant';

export interface LeaderboardEntry {
  discord_id: string;
  rank: string;
  points: number;
  matches_played: number;
  winrate: number; // 0–100
  streak: number;
}

export interface Leaderboard {
  rank_group: RankGroup;
  players: LeaderboardEntry[];
  last_updated: string; // ISO
}

export interface Match {
  match_id: string;
  players_red: string[];
  players_blue: string[];
  captain_red: string;
  captain_blue: string;
  lobby_master: string;
  rank_group: RankGroup;
  defense_start?: 'red' | 'blue';
  red_score?: number;
  blue_score?: number;
  result?: 'red' | 'blue' | 'cancelled';
  created_at: string; // ISO
  ended_at?: string; // ISO
  // Optional convenience fields on FE
  duration_ms?: number;
}

export interface Player {
  discord_id: string;
  riot_id: string;
  rank?: string;
  points: number;
  matches_played: number;
  wins: number;
  losses: number;
  winrate: number; // 0–100
}

export interface QueueEntry { discord_id: string }
export interface Queue { rank_group: RankGroup; players: QueueEntry[] }

export interface UserPreferences {
  discord_id: string;
  // Add fields as backend evolves
}
```

---

## 17. Example React Query Hooks (final)

```ts
import { useQuery, useInfiniteQuery } from '@tanstack/react-query';
import { leaderboardApi, matchesApi, playersApi, queueApi } from '../services/api';

export const useLeaderboard = (rankGroup: string) =>
  useQuery({
    queryKey: ['leaderboard', rankGroup],
    queryFn: () => leaderboardApi.getLeaderboard(rankGroup),
    staleTime: 60_000,
  });

export const useQueue = (rankGroup: string) =>
  useQuery({
    queryKey: ['queue', rankGroup],
    queryFn: () => queueApi.getQueue(rankGroup),
    refetchInterval: 15_000,
    staleTime: 10_000,
  });

export const useMatchHistory = (limit = 20) =>
  useInfiniteQuery({
    queryKey: ['matchHistory'],
    queryFn: ({ pageParam = 0 }) => matchesApi.getMatchHistory(limit + pageParam),
    getNextPageParam: (lastPage, allPages) => allPages.length * limit,
    staleTime: 60_000,
  });

export const usePlayers = (skip = 0, limit = 10) =>
  useQuery({
    queryKey: ['players', skip, limit],
    queryFn: () => playersApi.listPlayers(skip, limit),
    staleTime: 30_000,
  });
```

---

## 18. Checklist Additions
- [ ] Add React Query devtools in development only
- [ ] Instrument API error logging (Sentry)
- [ ] Virtualize long lists (leaderboard, players)
- [ ] Implement 429/5xx backoff banner
- [ ] Add a status indicator fed by `/healthz`
- [ ] CDN + hashed assets configured
- [ ] JWT decode tested end-to-end with `/auth/callback` 