import { useEffect, useState } from "react";
import { useAuth } from "@/hooks";
import { matchApi } from "@/api";
import { HistoryList } from "@/components/history";
import { LoadingPage, ErrorMessage } from "@/components/common";
import { Button } from "@/components/ui";
import { getErrorMessage } from "@/lib/errors";
import type { Match } from "@/types/api";

export default function History() {
  const { user } = useAuth();
  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const limit = 20;

  useEffect(() => {
    const fetchHistory = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await matchApi.getMatchHistory(user?.discord_id, limit, 0);
        setMatches(data);
        setHasMore(data.length === limit);
      } catch (e) {
        console.error("Failed to fetch match history:", e);
        setError(getErrorMessage(e));
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, [user?.discord_id]);

  const loadMore = async () => {
    const nextPage = page + 1;
    try {
      const data = await matchApi.getMatchHistory(
        user?.discord_id,
        limit,
        nextPage * limit
      );
      setMatches([...matches, ...data]);
      setPage(nextPage);
      setHasMore(data.length === limit);
    } catch (e) {
      console.error("Failed to load more matches:", e);
      setError(getErrorMessage(e));
    }
  };

  if (loading && matches.length === 0) {
    return <LoadingPage />;
  }

  if (error && matches.length === 0) {
    return (
      <ErrorMessage
        title="Failed to load history"
        message={error}
        onRetry={() => window.location.reload()}
      />
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-valorant-light">Match History</h1>
        <p className="text-valorant-gray mt-2">
          Your recent completed matches
        </p>
      </div>

      <HistoryList matches={matches} userDiscordId={user?.discord_id} />

      {hasMore && matches.length > 0 && (
        <div className="flex justify-center">
          <Button variant="secondary" onClick={loadMore}>
            Load More
          </Button>
        </div>
      )}
    </div>
  );
}
