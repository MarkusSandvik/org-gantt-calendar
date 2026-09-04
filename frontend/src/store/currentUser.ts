import { create } from "zustand";
import { persist } from "zustand/middleware";

interface CurrentUserState {
  userId: number | null;
  setUserId: (id: number | null) => void;
}

export const useCurrentUserStore = create<CurrentUserState>()(
  persist(
    (set) => ({
      userId: null,
      setUserId: (id) => set({ userId: id }),
    }),
    { name: "org-planner-current-user" },
  ),
);
