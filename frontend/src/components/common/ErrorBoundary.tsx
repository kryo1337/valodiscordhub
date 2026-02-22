import { Component, type ErrorInfo, type ReactNode } from "react";
import { Button } from "@/components/ui";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: undefined });
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4">
          <div className="text-valorant-red text-6xl mb-4">⚠</div>
          <h2 className="text-2xl font-semibold text-valorant-light">
            Something went wrong
          </h2>
          <p className="text-valorant-gray text-center max-w-md">
            An unexpected error occurred. Please try again or contact support if the
            problem persists.
          </p>
          {this.state.error && (
            <pre className="mt-4 p-4 bg-valorant-dark rounded-lg text-sm text-red-400 max-w-lg overflow-auto">
              {this.state.error.message}
            </pre>
          )}
          <div className="flex gap-4 mt-4">
            <Button onClick={this.handleReset}>Try Again</Button>
            <Button variant="secondary" onClick={() => window.location.reload()}>
              Reload Page
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
