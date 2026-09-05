const API_BASE = "/api/v1";
const CSRF_COOKIE_NAME = "csrf";
const MUTATING_METHODS = new Set(["POST", "PATCH", "PUT", "DELETE"]);

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

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
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

async function request<T>(
  path: string,
  init?: RequestInit,
  jsonBody = true,
): Promise<T> {
  const method = (init?.method ?? "GET").toUpperCase();
  const csrfToken = MUTATING_METHODS.has(method) ? getCookie(CSRF_COOKIE_NAME) : null;
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: {
      ...(jsonBody ? { "Content-Type": "application/json" } : {}),
      ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
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
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  delete: (path: string) => request<void>(path, { method: "DELETE" }),
  // No Content-Type header here — the browser sets multipart/form-data
  // with the correct boundary itself when the body is a FormData.
  postForm: <T>(path: string, formData: FormData) =>
    request<T>(path, { method: "POST", body: formData }, false),
};
