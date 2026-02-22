import { cn } from "@/lib/cn";
import type { HTMLAttributes, ReactNode } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  variant?: "default" | "accent";
}

export function Card({
  className,
  children,
  variant = "default",
  ...props
}: CardProps) {
  return (
    <div
      className={cn(
        "bg-gradient-to-b from-valorant-dark to-valorant-darker",
        "border-l-2 border-valorant-gray/20",
        variant === "accent" && "border-l-valorant-red",
        "shadow-lg shadow-black/20",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ className, children, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "px-5 py-4 border-b border-valorant-gray/10",
        "bg-gradient-to-r from-transparent via-valorant-gray/5 to-transparent",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardTitle({
  className,
  children,
  ...props
}: HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3
      className={cn(
        "text-lg font-bold text-valorant-light uppercase tracking-wider",
        className
      )}
      {...props}
    >
      {children}
    </h3>
  );
}

export function CardDescription({
  className,
  children,
  ...props
}: HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p
      className={cn("text-sm text-valorant-gray mt-1", className)}
      {...props}
    >
      {children}
    </p>
  );
}

export function CardContent({ className, children, ...props }: CardProps) {
  return (
    <div className={cn("px-5 py-4", className)} {...props}>
      {children}
    </div>
  );
}

export function CardFooter({ className, children, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "px-5 py-4 border-t border-valorant-gray/10 bg-valorant-darker/50",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
