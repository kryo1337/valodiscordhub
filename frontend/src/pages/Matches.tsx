import { useEffect, useState } from "react";
import { useMatchStore } from "@/stores";
import { matchApi } from "@/api";
import { MatchList } from "@/components/matches";
import { LoadingPage, ErrorMessage } from "@/components/common";
import { Button } from "@/components/ui";
import { getErrorMessage } from "@/lib/errors";
import { RefreshCw } from "lucide-react";

export default function Matches() {
  const { activeMatches, setActiveMatches, loading, setLoading, error, setError } =
    useMatchStore();
  const [refreshing, setRefreshing] = useState(false);

  const fetchMatches = async () => {
    setLoading(true);
    setError(null);
    try {
      const matches = await matchApi.getActiveMatches();
      setActiveMatches(matches);
      } catch (e) {
        console.error("Failed to fetch matches:", e);
        setError(getErrorMessage(e));
      } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMatches();
  }, [setActiveMatches, setLoading, setError]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchMatches();
    setRefreshing(false);
  };

  if (loading && activeMatches.length === 0) {
    return <LoadingPage />;
  }

  if (error && activeMatches.length === 0) {
    return (
      <ErrorMessage
        title="Failed to load matches"
        message={error}
        onRetry={fetchMatches}
      />
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-valorant-light">Active Matches</h1>
          <p className="text-valorant-gray mt-2">
            Currently ongoing matches across all rank groups
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={handleRefresh}
          disabled={refreshing}
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      <MatchList
        matches={activeMatches}
        emptyMessage="No active matches"
      />
    </div>
  );
}
