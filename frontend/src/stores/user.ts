import { create } from "zustand";
import { devtools } from "zustand/middleware";
import { getCurrentUser, isAuthenticated } from "@/api/auth";
import type { User } from "@/types/api";

interface UserState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setUser: (user: User | null) => void;
  setLoading: (loading: boolean) => void;
  clearUser: () => void;
  initialize: () => void;
}

export const useUserStore = create<UserState>()(
  devtools(
    (set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  setUser: (user) => set({ user, isAuthenticated: !!user }),
  setLoading: (isLoading) => set({ isLoading }),
  clearUser: () => {
    localStorage.removeItem("jwt");
    localStorage.removeItem("user");
    set({ user: null, isAuthenticated: false });
  },
  initialize: () => {
    const user = getCurrentUser();
    const authenticated = isAuthenticated();
    set({ user, isAuthenticated: authenticated, isLoading: false });
  },
}),
    { name: "UserStore" }
  )
);
