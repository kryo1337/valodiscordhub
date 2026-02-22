import { useEffect } from "react";
import { useUserStore } from "@/stores/user";
import { getCurrentUser } from "@/api/auth";

export function useAuth() {
  const { user, isAuthenticated: isAuth, isLoading, setUser, setLoading, clearUser } = useUserStore();

  useEffect(() => {
    const storedUser = getCurrentUser();
    setUser(storedUser);
    setLoading(false);
  }, [setUser, setLoading]);

  return {
    user,
    isAuthenticated: isAuth,
    isLoading,
    logout: clearUser,
  };
}
