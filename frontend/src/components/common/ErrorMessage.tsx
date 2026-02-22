import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui";

interface ErrorMessageProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
}

export function ErrorMessage({
  title = "Error",
  message = "Something went wrong. Please try again.",
  onRetry,
}: ErrorMessageProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-6 py-12">
      <div className="p-4 bg-valorant-red/10 border-l-2 border-valorant-red">
        <AlertTriangle className="h-8 w-8 text-valorant-red" />
      </div>
      <h3 className="text-sm font-bold text-valorant-light uppercase tracking-widest">
        {title}
      </h3>
      <p className="text-sm text-valorant-gray text-center max-w-md leading-relaxed">
        {message}
      </p>
      {onRetry && (
        <Button variant="outline" onClick={onRetry}>
          <RefreshCw className="h-4 w-4 skew-x-[3deg]" />
          Try Again
        </Button>
      )}
    </div>
  );
}
