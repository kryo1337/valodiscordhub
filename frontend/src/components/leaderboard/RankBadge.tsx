import { cn } from "@/lib/cn";

interface RankBadgeProps {
  rank: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const rankColors: Record<string, string> = {
  iron: "border-gray-500 text-gray-400 bg-gray-500/10",
  bronze: "border-amber-600 text-amber-500 bg-amber-600/10",
  silver: "border-gray-400 text-gray-300 bg-gray-400/10",
  gold: "border-yellow-500 text-yellow-400 bg-yellow-500/10",
  platinum: "border-cyan-400 text-cyan-300 bg-cyan-400/10",
  diamond: "border-purple-400 text-purple-300 bg-purple-400/10",
  ascendant: "border-green-400 text-green-300 bg-green-400/10",
  immortal: "border-red-400 text-red-300 bg-red-400/10",
  radiant: "border-yellow-300 text-yellow-200 bg-yellow-300/10",
};

export function RankBadge({ rank, size = "md", className }: RankBadgeProps) {
  if (!rank) {
    return (
      <span className={cn("text-valorant-gray/50 text-xs uppercase tracking-wider", className)}>
        Unranked
      </span>
    );
  }

  const rankLower = rank.toLowerCase();
  const baseRank = Object.keys(rankColors).find((r) => rankLower.startsWith(r));
  const colorClasses = baseRank ? rankColors[baseRank] : "border-valorant-gray text-valorant-gray bg-valorant-gray/10";

  const sizes = {
    sm: "px-2 py-0.5 text-[10px]",
    md: "px-3 py-1 text-xs",
    lg: "px-4 py-1.5 text-sm",
  };

  const formatRank = (r: string): string => {
    return r
      .split(/[\s_-]+/)
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(" ");
  };

  return (
    <span
      className={cn(
        "inline-flex items-center font-bold uppercase tracking-wider",
        "border-l-2",
        colorClasses,
        sizes[size],
        className
      )}
    >
      {formatRank(rank)}
    </span>
  );
}
