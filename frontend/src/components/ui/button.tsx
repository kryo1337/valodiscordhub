import { cn } from "@/lib/cn";
import type { ButtonHTMLAttributes } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost" | "outline";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
}

export function Button({
  variant = "primary",
  size = "md",
  className,
  children,
  disabled,
  isLoading,
  ...props
}: ButtonProps) {
  const variants = {
    primary:
      "bg-valorant-red hover:bg-valorant-red-dark text-white shadow-[inset_0_-3px_0_rgba(0,0,0,0.3)] hover:shadow-[inset_0_-3px_0_rgba(0,0,0,0.4)]",
    secondary:
      "bg-valorant-dark hover:bg-valorant-gray/20 text-valorant-light border-2 border-valorant-gray/30",
    danger:
      "bg-red-700 hover:bg-red-800 text-white shadow-[inset_0_-3px_0_rgba(0,0,0,0.3)]",
    ghost:
      "bg-transparent hover:bg-valorant-red/10 text-valorant-light hover:text-valorant-red",
    outline:
      "bg-transparent hover:bg-valorant-red text-valorant-red hover:text-white border-2 border-valorant-red transition-all",
  };

  const sizes = {
    sm: "px-4 py-2 text-xs uppercase tracking-wider font-bold",
    md: "px-6 py-3 text-sm uppercase tracking-wider font-bold",
    lg: "px-8 py-4 text-sm uppercase tracking-wider font-bold",
  };

  return (
    <button
      className={cn(
        "skew-x-[-3deg] rounded-sm font-medium transition-all duration-150",
        "inline-flex items-center justify-center gap-2",
        "[&>*]:skew-x-[3deg]",
        "disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:shadow-[inset_0_-3px_0_rgba(0,0,0,0.3)]",
        "active:translate-y-[2px] active:shadow-none",
        variants[variant],
        sizes[size],
        className
      )}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading && (
        <svg
          className="animate-spin h-4 w-4"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      )}
      {children}
    </button>
  );
}
