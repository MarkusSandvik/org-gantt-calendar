import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";
import type { Me } from "../api/types";

export const ME_QUERY_KEY = ["auth", "me"];

/** The logged-in user, or null if not authenticated. `isLoading` is only
 * true on the very first check — after that a 401 just means `me` is
 * null, so callers can render a login prompt instead of a spinner. */
export function useCurrentUser() {
  const query = useQuery({
    queryKey: ME_QUERY_KEY,
    queryFn: () => api.get<Me>("/auth/me"),
    retry: false,
    staleTime: 60_000,
  });
  const isUnauthenticated = query.isError && query.error instanceof ApiError && query.error.status === 401;
  return {
    me: query.data ?? null,
    isLoading: query.isLoading,
    isUnauthenticated,
  };
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { email: string; password: string }) =>
      api.post<Me>("/auth/login", payload),
    onSuccess: (me) => {
      queryClient.setQueryData(ME_QUERY_KEY, me);
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.post("/auth/logout"),
    onSuccess: () => {
      queryClient.setQueryData(ME_QUERY_KEY, null);
      queryClient.clear();
    },
  });
}

export function isLead(me: Me | null, teamId: number | null | undefined): boolean {
  if (!me || teamId == null) return false;
  return me.team_memberships.some((m) => m.team_id === teamId && m.team_role === "lead");
}

export function isAdmin(me: Me | null): boolean {
  return me?.global_role === "admin";
}

export function isAssigned(
  me: Me | null,
  ownerUserId: number | null | undefined,
  contributorIds: number[],
): boolean {
  if (!me) return false;
  return me.id === ownerUserId || contributorIds.includes(me.id);
}
