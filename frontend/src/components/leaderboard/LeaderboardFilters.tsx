import { Button } from "@/components/ui";
import { formatRankGroupShort } from "@/lib/format";
import type { RankGroup } from "@/types/api";

interface LeaderboardFiltersProps {
  selectedRankGroup: RankGroup;
  onRankGroupChange: (rankGroup: RankGroup) => void;
}

const RANK_GROUPS: RankGroup[] = ["iron-plat", "dia-asc", "imm-radiant"];

export function LeaderboardFilters({
  selectedRankGroup,
  onRankGroupChange,
}: LeaderboardFiltersProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {RANK_GROUPS.map((rg) => (
        <Button
          key={rg}
          variant={selectedRankGroup === rg ? "primary" : "secondary"}
          size="sm"
          onClick={() => onRankGroupChange(rg)}
        >
          {formatRankGroupShort(rg)}
        </Button>
      ))}
    </div>
  );
}
