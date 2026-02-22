import { cn } from "@/lib/cn";

interface BadgeProps {
  variant?: "default" | "success" | "warning" | "danger" | "info";
  size?: "sm" | "md";
  children: React.ReactNode;
  className?: string;
}

export function Badge({
  variant = "default",
  size = "sm",
  children,
  className,
}: BadgeProps) {
  const variants = {
    default: "bg-valorant-gray/20 text-valorant-gray border-valorant-gray/30",
    success: "bg-valorant-cyan/20 text-valorant-cyan border-valorant-cyan/30",
    warning: "bg-valorant-gold/20 text-valorant-gold border-valorant-gold/30",
    danger: "bg-valorant-red/20 text-valorant-red border-valorant-red/30",
    info: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  };

  const sizes = {
    sm: "px-2 py-0.5 text-[10px]",
    md: "px-3 py-1 text-xs",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center font-bold uppercase tracking-wider",
        "border-l-2",
        variants[variant],
        sizes[size],
        className
      )}
    >
      {children}
    </span>
  );
}
