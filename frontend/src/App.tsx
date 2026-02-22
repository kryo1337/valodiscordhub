import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useEffect } from "react";
import { useUserStore } from "./stores/user";
import { useWebSocket } from "./hooks/useWebSocket";
import { getToken } from "./api/auth";
import { Header } from "./components/layout/Header";
import { Footer } from "./components/layout/Footer";
import { ErrorBoundary, LoadingPage, ConnectionStatus, ToastContainer } from "./components/common";
import {
  Home,
  Queue,
  Matches,
  Leaderboard,
  History,
  Profile,
  Login,
  Callback,
} from "./pages";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useUserStore();

  if (isLoading) {
    return <LoadingPage />;
  }

  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
}

function AppContent() {
  const { initialize, isAuthenticated } = useUserStore();
  const token = getToken();

  useEffect(() => {
    initialize();
  }, [initialize]);

  useWebSocket(isAuthenticated ? token : null);

  return (
    <div className="min-h-screen flex flex-col bg-valorant-darker text-valorant-light">
      <ConnectionStatus />
      <Header />
      <ToastContainer />
      <main className="flex-1 container mx-auto px-4 py-8">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/callback" element={<Callback />} />
          <Route
            path="/queue"
            element={
              <ProtectedRoute>
                <Queue />
              </ProtectedRoute>
            }
          />
          <Route
            path="/matches"
            element={
              <ProtectedRoute>
                <Matches />
              </ProtectedRoute>
            }
          />
          <Route
            path="/leaderboard"
            element={
              <ProtectedRoute>
                <Leaderboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/history"
            element={
              <ProtectedRoute>
                <History />
              </ProtectedRoute>
            }
          />
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <Profile />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <Footer />
    </div>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AppContent />
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;
