import { Trophy, Medal, Award } from "lucide-react";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui";
import { Avatar } from "@/components/common";
import { RankBadge } from "./RankBadge";
import { formatWinrate } from "@/lib/format";
import { cn } from "@/lib/cn";
import type { LeaderboardEntry } from "@/types/api";

interface LeaderboardTableProps {
  entries: LeaderboardEntry[];
}

function RankIcon({ rank }: { rank: number }) {
  if (rank === 1) {
    return <Trophy className="h-5 w-5 text-yellow-400" />;
  }
  if (rank === 2) {
    return <Medal className="h-5 w-5 text-gray-300" />;
  }
  if (rank === 3) {
    return <Award className="h-5 w-5 text-amber-600" />;
  }
  return <span className="text-sm text-valorant-gray">#{rank}</span>;
}

export function LeaderboardTable({ entries }: LeaderboardTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-16">Rank</TableHead>
          <TableHead>Player</TableHead>
          <TableHead className="hidden sm:table-cell">Valorant Rank</TableHead>
          <TableHead className="text-right">Points</TableHead>
          <TableHead className="text-right hidden md:table-cell">W/L</TableHead>
          <TableHead className="text-right hidden md:table-cell">Win Rate</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {entries.map((entry, index) => (
          <TableRow
            key={entry.discord_id}
            className={cn(
              index < 3 && "bg-valorant-red/5"
            )}
          >
            <TableCell className="font-medium">
              <div className="flex items-center justify-center">
                <RankIcon rank={entry.rank} />
              </div>
            </TableCell>
            <TableCell>
              <div className="flex items-center gap-3">
                <Avatar
                  src={entry.avatar_url}
                  alt={entry.riot_id}
                  fallback={entry.riot_id?.charAt(0)}
                  size="sm"
                />
                <div>
                  <div className="font-medium text-valorant-light">
                    {entry.riot_id || `Player #${entry.discord_id.slice(-4)}`}
                  </div>
                  <div className="text-xs text-valorant-gray sm:hidden">
                    <RankBadge rank={entry.rank_val} size="sm" />
                  </div>
                </div>
              </div>
            </TableCell>
            <TableCell className="hidden sm:table-cell">
              <RankBadge rank={entry.rank_val} />
            </TableCell>
            <TableCell className="text-right font-bold text-valorant-red">
              {entry.points}
            </TableCell>
            <TableCell className="text-right hidden md:table-cell">
              <span className="text-green-400">{entry.wins}</span>
              <span className="text-valorant-gray/50 mx-1">/</span>
              <span className="text-red-400">{entry.losses}</span>
            </TableCell>
            <TableCell className="text-right hidden md:table-cell">
              <span
                className={cn(
                  entry.winrate >= 0.5 ? "text-green-400" : "text-valorant-gray"
                )}
              >
                {formatWinrate(entry.winrate)}
              </span>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
