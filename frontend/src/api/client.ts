import { useCurrentUserStore } from "../store/currentUser";

const API_BASE = "/api/v1";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

interface FastApiValidationError {
  loc: (string | number)[];
  msg: string;
}

/** FastAPI errors are either a plain string (HTTPException) or a list of
 * pydantic validation errors (422). Extract a human-readable message from
 * either shape, falling back to the raw body if it's neither. */
function extractErrorMessage(bodyText: string): string {
  try {
    const parsed = JSON.parse(bodyText) as { detail?: unknown };
    if (typeof parsed.detail === "string") {
      return parsed.detail;
    }
    if (Array.isArray(parsed.detail)) {
      return (parsed.detail as FastApiValidationError[])
        .map((e) => e.msg)
        .join("; ");
    }
  } catch {
    // Not JSON — fall through to the raw text.
  }
  return bodyText;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const userId = useCurrentUserStore.getState().userId;
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(userId != null ? { "X-User-Id": String(userId) } : {}),
      ...(init?.headers ?? {}),
    },
    ...init,
  });
  if (!res.ok) {
    throw new ApiError(res.status, extractErrorMessage(await res.text()));
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  delete: (path: string) => request<void>(path, { method: "DELETE" }),
};
