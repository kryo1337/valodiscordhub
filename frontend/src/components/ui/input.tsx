import { cn } from "@/lib/cn";
import type { InputHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export function Input({
  className,
  label,
  error,
  id,
  ...props
}: InputProps) {
  return (
    <div className="space-y-2">
      {label && (
        <label
          htmlFor={id}
          className="block text-xs uppercase tracking-wider font-bold text-valorant-gray"
        >
          {label}
        </label>
      )}
      <input
        id={id}
        className={cn(
          "w-full px-4 py-3",
          "bg-valorant-darker border-l-2 border-valorant-gray/30",
          "text-valorant-light placeholder:text-valorant-gray/30",
          "focus:outline-none focus:border-valorant-red focus:bg-valorant-dark",
          "transition-all duration-150",
          error && "border-valorant-red",
          className
        )}
        {...props}
      />
      {error && (
        <p className="text-xs text-valorant-red uppercase tracking-wide">{error}</p>
      )}
    </div>
  );
}
