import { cn } from "@/lib/cn";

// --- Base skeleton ---

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        "animate-pulse rounded bg-valorant-gray/20",
        className
      )}
      aria-hidden="true"
    />
  );
}

// --- Skeleton variants ---

// Card skeleton
export function SkeletonCard() {
  return (
    <div className="rounded-lg border border-valorant-gray/10 bg-valorant-dark/50 p-6">
      <div className="flex items-start justify-between mb-4">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-6 w-6" />
      </div>
      <Skeleton className="h-4 w-full mb-3" />
      <Skeleton className="h-4 w-3/4 mb-3" />
      <Skeleton className="h-4 w-1/2" />
    </div>
  );
}

// List item skeleton
export function SkeletonListItem({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "flex items-center gap-4 p-4 border border-valorant-gray/10 rounded-lg bg-valorant-dark/30",
        className
      )}
    >
      <Skeleton className="h-10 w-10 rounded-full" />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-3 w-32" />
      </div>
      <Skeleton className="h-6 w-20" />
    </div>
  );
}

// Table skeleton
export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="w-full">
      {/* Header */}
      <div className="flex gap-4 p-3 border-b border-valorant-gray/10 mb-2">
        <Skeleton className="h-4 w-16" />
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-4 w-20" />
        <Skeleton className="h-4 w-16" />
      </div>

      {/* Rows */}
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="flex gap-4 p-3 border-b border-valorant-gray/5 items-center"
        >
          <Skeleton className="h-4 w-8" />
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-4 w-16" />
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-4 w-16" />
          <Skeleton className="h-4 w-16" />
        </div>
      ))}
    </div>
  );
}

// Stats skeleton (for profile stats card)
export function SkeletonStats() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="p-4 rounded-lg border border-valorant-gray/10 bg-valorant-dark/30">
          <Skeleton className="h-3 w-16 mb-2" />
          <Skeleton className="h-8 w-20" />
        </div>
      ))}
    </div>
  );
}

// Queue card skeleton
export function SkeletonQueueCard() {
  return (
    <div className="rounded-lg border border-valorant-gray/10 bg-valorant-dark/50 p-6">
      <div className="flex items-center justify-between mb-4">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-8 w-16 rounded" />
      </div>

      {/* Player list skeleton */}
      <div className="space-y-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>

      <div className="mt-4 pt-4 border-t border-valorant-gray/10">
        <Skeleton className="h-10 w-full rounded" />
      </div>
    </div>
  );
}

// Match card skeleton
export function SkeletonMatchCard() {
  return (
    <div className="rounded-lg border border-valorant-gray/10 bg-valorant-dark/50 p-5">
      <div className="flex items-start justify-between mb-4">
        <Skeleton className="h-5 w-24" />
        <Skeleton className="h-6 w-20 rounded-full" />
      </div>

      {/* Teams */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="space-y-2">
          <Skeleton className="h-4 w-12" />
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-8 w-full" />
          ))}
        </div>
        <div className="space-y-2">
          <Skeleton className="h-4 w-12" />
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-8 w-full" />
          ))}
        </div>
      </div>

      <div className="flex items-center justify-between pt-4 border-t border-valorant-gray/10">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-10 w-32 rounded" />
      </div>
    </div>
  );
}

// Loading list with skeleton items
interface SkeletonListProps {
  count?: number;
}

export function SkeletonList({ count = 5 }: SkeletonListProps) {
  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonListItem key={i} />
      ))}
    </div>
  );
}

// Loading grid with skeleton cards
interface SkeletonGridProps {
  cols?: number;
  count?: number;
}

export function SkeletonGrid({ cols = 3, count = 6 }: SkeletonGridProps) {
  return (
    <div className={`grid grid-cols-1 md:grid-cols-${Math.min(cols, 2)} lg:grid-cols-${cols} gap-4`}>
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}
