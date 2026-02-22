import { useEffect, useState } from "react";
import { useAuth } from "@/hooks";
import { playerApi } from "@/api";
import { StatsCard } from "@/components/stats";
import { RankBadge } from "@/components/leaderboard";
import { Avatar, LoadingPage, ErrorMessage } from "@/components/common";
import { getErrorMessage } from "@/lib/errors";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui";
import { Shield } from "lucide-react";
import type { Player } from "@/types/api";

export default function Profile() {
  const { user } = useAuth();
  const [player, setPlayer] = useState<Player | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPlayer = async () => {
      if (!user?.discord_id) return;

      setLoading(true);
      setError(null);
      try {
        const data = await playerApi.getPlayer(user.discord_id);
        setPlayer(data);
      } catch (e) {
        console.error("Failed to fetch player:", e);
        setError(getErrorMessage(e));
      } finally {
        setLoading(false);
      }
    };
    fetchPlayer();
  }, [user?.discord_id]);

  if (loading) {
    return <LoadingPage />;
  }

  if (error) {
    return (
      <ErrorMessage
        title="Failed to load profile"
        message={error}
        onRetry={() => window.location.reload()}
      />
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-valorant-light">Profile</h1>
        <p className="text-valorant-gray mt-2">Your player profile and stats</p>
      </div>

      {/* Profile Card */}
      <Card>
        <CardContent className="py-8">
          <div className="flex flex-col md:flex-row items-center gap-6">
            <Avatar
              src={user?.avatar}
              alt={user?.username}
              fallback={user?.username?.charAt(0)}
              size="lg"
              className="h-24 w-24 text-2xl"
            />
            <div className="text-center md:text-left">
              <h2 className="text-2xl font-bold text-valorant-light">
                {player?.riot_id || user?.username}
              </h2>
              <p className="text-valorant-gray">@{user?.username}</p>
              <div className="mt-3">
                <RankBadge rank={player?.rank || ""} size="lg" />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats */}
      {player && <StatsCard player={player} />}

      {/* Account Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-valorant-red" />
            Account Information
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between py-2 border-b border-valorant-gray/10">
            <span className="text-valorant-gray">Discord ID</span>
            <span className="text-valorant-light font-mono">{user?.discord_id}</span>
          </div>
          <div className="flex items-center justify-between py-2 border-b border-valorant-gray/10">
            <span className="text-valorant-gray">Riot ID</span>
            <span className="text-valorant-light">
              {player?.riot_id || "Not set"}
            </span>
          </div>
          <div className="flex items-center justify-between py-2">
            <span className="text-valorant-gray">Current Rank</span>
            <RankBadge rank={player?.rank || ""} />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
