import { Link } from "react-router-dom";
import { Button } from "@/components/ui";
import { MessageCircle } from "lucide-react";
import { login } from "@/api/auth";

export default function Login() {
  const handleLogin = () => {
    login();
  };

  return (
    <div className="min-h-[70vh] flex items-center justify-center">
      <div className="text-center max-w-md">
        <div className="mb-8">
          <div className="h-20 w-20 bg-valorant-red rounded-xl flex items-center justify-center mx-auto mb-6">
            <span className="text-white font-bold text-4xl">V</span>
          </div>
          <h1 className="text-3xl font-bold mb-2">Welcome to ValoHub</h1>
          <p className="text-valorant-gray">
            Sign in with your Discord account to join competitive custom matches.
          </p>
        </div>

        <Button size="lg" className="w-full" onClick={handleLogin}>
          <MessageCircle className="h-5 w-5 mr-2" />
          Login with Discord
        </Button>

        <p className="text-xs text-valorant-gray/50 mt-6">
          By signing in, you agree to our terms of service and privacy policy.
        </p>

        <Link
          to="/"
          className="block mt-8 text-sm text-valorant-gray hover:text-valorant-light transition-colors"
        >
          &larr; Back to home
        </Link>
      </div>
    </div>
  );
}
