import { useEffect } from "react";
import { useLeaderboardStore } from "@/stores";
import { playerApi } from "@/api";
import { LeaderboardTable, LeaderboardFilters } from "@/components/leaderboard";
import { LoadingPage, ErrorMessage, EmptyState } from "@/components/common";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui";
import { getErrorMessage } from "@/lib/errors";
import { Trophy } from "lucide-react";
import type { RankGroup } from "@/types/api";

export default function Leaderboard() {
  const {
    entries,
    selectedRankGroup,
    setEntries,
    setSelectedRankGroup,
    loading,
    setLoading,
    error,
    setError,
  } = useLeaderboardStore();

  useEffect(() => {
    const fetchLeaderboard = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await playerApi.getLeaderboard(selectedRankGroup);
        setEntries(selectedRankGroup, data);
      } catch (e) {
        console.error("Failed to fetch leaderboard:", e);
        setError(getErrorMessage(e));
      } finally {
        setLoading(false);
      }
    };
    fetchLeaderboard();
  }, [selectedRankGroup, setEntries, setLoading, setError]);

  const handleRankGroupChange = (rankGroup: RankGroup) => {
    setSelectedRankGroup(rankGroup);
  };

  const currentEntries = entries[selectedRankGroup] || [];

  if (loading && currentEntries.length === 0) {
    return <LoadingPage />;
  }

  if (error && currentEntries.length === 0) {
    return (
      <ErrorMessage
        title="Failed to load leaderboard"
        message={error}
        onRetry={() => window.location.reload()}
      />
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-valorant-light">Leaderboard</h1>
        <p className="text-valorant-gray mt-2">
          Top players ranked by performance
        </p>
      </div>

      <LeaderboardFilters
        selectedRankGroup={selectedRankGroup}
        onRankGroupChange={handleRankGroupChange}
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Trophy className="h-5 w-5 text-valorant-red" />
            Rankings
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {currentEntries.length > 0 ? (
            <LeaderboardTable entries={currentEntries} />
          ) : (
            <EmptyState
              icon={<Trophy className="h-16 w-16" />}
              title="No players yet"
              description="Be the first to play and appear on the leaderboard!"
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
