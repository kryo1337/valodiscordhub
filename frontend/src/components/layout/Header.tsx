import { Link, useLocation } from "react-router-dom";
import { Users, Swords, Trophy, History, LogOut, Menu, X } from "lucide-react";
import { useState, useEffect } from "react";
import { useAuth } from "@/hooks";
import { Avatar } from "@/components/common";
import { Button } from "@/components/ui";
import { cn } from "@/lib/cn";

const navLinks = [
  { to: "/queue", label: "Queue", icon: Users },
  { to: "/matches", label: "Matches", icon: Swords },
  { to: "/leaderboard", label: "Leaderboard", icon: Trophy },
  { to: "/history", label: "History", icon: History },
];

export function Header() {
  const { user, isAuthenticated, logout } = useAuth();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  return (
    <header className="sticky top-0 z-50 bg-valorant-darker/95 backdrop-blur-sm border-b-2 border-valorant-gray/10">
      <div className="container mx-auto px-4">
        <div className="flex h-16 items-center justify-between">
          <Link to="/" className="flex items-center gap-3 group">
            <div className="relative">
              <div className="absolute inset-0 bg-valorant-red blur-sm opacity-50 group-hover:opacity-100 transition-opacity" />
              <div className="relative h-9 w-9 bg-valorant-red flex items-center justify-center skew-x-[-6deg]">
                <span className="text-white font-black text-xl skew-x-[6deg]">V</span>
              </div>
            </div>
            <span className="font-black text-xl text-valorant-light tracking-tight hidden sm:block">
              VALO<span className="text-valorant-red">HUB</span>
            </span>
          </Link>

          {isAuthenticated && (
            <nav className="hidden md:flex items-center">
              {navLinks.map(({ to, label, icon: Icon }) => (
                <Link
                  key={to}
                  to={to}
                  className={cn(
                    "flex items-center gap-2 px-5 py-5 text-xs uppercase tracking-widest font-bold",
                    "border-b-2 transition-all duration-200",
                    location.pathname === to
                      ? "border-valorant-red text-valorant-light bg-valorant-red/5"
                      : "border-transparent text-valorant-gray hover:text-valorant-light hover:border-valorant-gray/30"
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </Link>
              ))}
            </nav>
          )}

          <div className="flex items-center gap-3">
            {isAuthenticated ? (
              <>
                <Link
                  to="/profile"
                  className="flex items-center gap-3 px-3 py-2 hover:bg-valorant-gray/10 transition-colors"
                >
                  <Avatar
                    src={user?.avatar}
                    alt={user?.username}
                    size="sm"
                  />
                  <span className="hidden sm:block text-sm text-valorant-light font-medium">
                    {user?.username}
                  </span>
                </Link>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={logout}
                  className="hidden sm:flex"
                  aria-label="Log out"
                >
                  <LogOut className="h-4 w-4" />
                </Button>
              </>
            ) : (
              <Link to="/login">
                <Button size="sm">Login</Button>
              </Link>
            )}

            <button
              className="md:hidden p-3 text-valorant-gray hover:text-valorant-light hover:bg-valorant-gray/10 transition-colors"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
              aria-expanded={mobileMenuOpen}
            >
              {mobileMenuOpen ? (
                <X className="h-5 w-5" />
              ) : (
                <Menu className="h-5 w-5" />
              )}
            </button>
          </div>
        </div>

        {mobileMenuOpen && isAuthenticated && (
          <nav className="md:hidden border-t border-valorant-gray/10">
            {navLinks.map(({ to, label, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                onClick={() => setMobileMenuOpen(false)}
                className={cn(
                  "flex items-center gap-4 px-4 py-4 text-sm font-medium border-l-2 transition-colors",
                  location.pathname === to
                    ? "border-valorant-red text-valorant-light bg-valorant-red/5"
                    : "border-transparent text-valorant-gray hover:text-valorant-light hover:border-valorant-gray/30"
                )}
              >
                <Icon className="h-5 w-5" />
                <span className="uppercase tracking-wider text-xs">{label}</span>
              </Link>
            ))}
            <button
              onClick={logout}
              className="flex items-center gap-4 px-4 py-4 text-sm font-medium text-valorant-gray hover:text-valorant-red w-full border-l-2 border-transparent hover:border-valorant-red/30 transition-colors"
              aria-label="Log out"
            >
              <LogOut className="h-5 w-5" />
              <span className="uppercase tracking-wider text-xs">Logout</span>
            </button>
          </nav>
        )}
      </div>
    </header>
  );
}
