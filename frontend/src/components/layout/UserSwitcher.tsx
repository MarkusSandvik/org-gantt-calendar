import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { api } from "../../api/client";
import type { User } from "../../api/types";
import { useCurrentUserStore } from "../../store/currentUser";

export function UserSwitcher() {
  const { data: users } = useQuery({
    queryKey: ["users"],
    queryFn: () => api.get<User[]>("/users"),
  });
  const userId = useCurrentUserStore((s) => s.userId);
  const setUserId = useCurrentUserStore((s) => s.setUserId);

  useEffect(() => {
    if (userId == null && users && users.length > 0) {
      setUserId(users[0].id);
    }
  }, [userId, users, setUserId]);

  if (!users || users.length === 0) {
    return null;
  }

  return (
    <div className="user-switcher">
      <label htmlFor="acting-as">Acting as</label>
      <select
        id="acting-as"
        value={userId ?? ""}
        onChange={(e) => setUserId(Number(e.target.value))}
      >
        {users.map((user) => (
          <option key={user.id} value={user.id}>
            {user.name} ({user.role})
          </option>
        ))}
      </select>
    </div>
  );
}
