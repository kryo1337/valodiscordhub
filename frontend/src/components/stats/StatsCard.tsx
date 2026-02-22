import { Trophy, Target, TrendingUp, Swords } from "lucide-react";
import { Card, CardContent } from "@/components/ui";
import { formatWinrate } from "@/lib/format";
import type { Player } from "@/types/api";

interface StatsCardProps {
  player: Player;
}

export function StatsCard({ player }: StatsCardProps) {
  const stats = [
    {
      label: "Points",
      value: player.points,
      icon: Trophy,
      color: "text-valorant-red",
    },
    {
      label: "Matches",
      value: player.matches_played,
      icon: Swords,
      color: "text-valorant-light",
    },
    {
      label: "Wins",
      value: player.wins,
      icon: Target,
      color: "text-green-400",
    },
    {
      label: "Win Rate",
      value: formatWinrate(player.winrate),
      icon: TrendingUp,
      color: player.winrate >= 0.5 ? "text-green-400" : "text-valorant-gray",
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {stats.map(({ label, value, icon: Icon, color }) => (
        <Card key={label}>
          <CardContent className="py-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-valorant-darker">
                <Icon className={`h-5 w-5 ${color}`} />
              </div>
              <div>
                <p className="text-sm text-valorant-gray">{label}</p>
                <p className={`text-xl font-bold ${color}`}>{value}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
