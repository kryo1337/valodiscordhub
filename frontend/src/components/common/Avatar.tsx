import * as AvatarPrimitive from "@radix-ui/react-avatar";
import { cn } from "@/lib/cn";

interface AvatarProps {
  src?: string | null;
  alt?: string;
  fallback?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function Avatar({
  src,
  alt = "Avatar",
  fallback,
  size = "md",
  className,
}: AvatarProps) {
  const sizes = {
    sm: "h-8 w-8 text-xs",
    md: "h-10 w-10 text-sm",
    lg: "h-14 w-14 text-base",
  };

  const initials = fallback || alt?.charAt(0).toUpperCase() || "?";

  return (
    <AvatarPrimitive.Root
      className={cn(
        "relative flex shrink-0 overflow-hidden rounded-full",
        sizes[size],
        className
      )}
    >
      <AvatarPrimitive.Image
        src={src || undefined}
        alt={alt}
        className="aspect-square h-full w-full object-cover"
      />
      <AvatarPrimitive.Fallback
        className={cn(
          "flex h-full w-full items-center justify-center rounded-full",
          "bg-valorant-red text-white font-semibold"
        )}
        delayMs={600}
      >
        {initials}
      </AvatarPrimitive.Fallback>
    </AvatarPrimitive.Root>
  );
}
