import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { handleCallback } from "@/api/auth";
import { useUserStore } from "@/stores";
import { LoadingPage, ErrorMessage } from "@/components/common";

export default function Callback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { setUser } = useUserStore();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get("code");

    if (!code) {
      setError("No authorization code provided");
      return;
    }

    const authenticate = async () => {
      try {
        const response = await handleCallback(code);
        setUser(response.user);
        navigate("/queue", { replace: true });
      } catch (e) {
        console.error("Authentication failed:", e);
        setError("Authentication failed. Please try again.");
      }
    };

    authenticate();
  }, [searchParams, navigate, setUser]);

  if (error) {
    return (
      <div className="min-h-[70vh] flex items-center justify-center">
        <ErrorMessage
          title="Authentication Failed"
          message={error}
          onRetry={() => navigate("/login")}
        />
      </div>
    );
  }

  return (
    <div className="min-h-[70vh] flex items-center justify-center">
      <LoadingPage />
    </div>
  );
}
