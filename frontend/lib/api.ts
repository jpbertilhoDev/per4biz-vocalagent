const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

export const AUTH_TOKEN_STORAGE_KEY = "vox-auth-token";

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string
  ) {
    super(`API ${status}: ${detail}`);
    this.name = "ApiError";
  }
}

const RETRYABLE_STATUS_CODES = new Set([429, 500, 502, 503, 504]);
const MAX_RETRIES = 2;
const BASE_DELAY_MS = 1000;

async function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Read the session JWT from localStorage. Used as a fallback to the
 * cookie auth when the browser blocks cross-site cookies (Chrome 3rd-party
 * cookie deprecation 2024+). The token is extracted from the auth callback
 * redirect fragment on `/` — see app/page.tsx.
 */
export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function clearAuthToken(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  } catch {
    // ignore
  }
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_URL}${path}`;
  const token = getAuthToken();

  let lastError: ApiError | null = null;

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    if (attempt > 0) {
      const delay = Math.min(BASE_DELAY_MS * 2 ** (attempt - 1), 8000);
      await sleep(delay);
    }

    const response = await fetch(url, {
      ...options,
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers ?? {}),
      },
    });

    if (response.ok) {
      return response.json();
    }

    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // body não é JSON — mantém statusText
    }

    // 401 — clear stale token + redirect to login (re-auth) — never retry
    if (response.status === 401 && typeof window !== "undefined") {
      clearAuthToken();
      window.location.href = "/";
      throw new ApiError(response.status, detail);
    }

    // Non-retryable client errors (4xx except 429)
    if (response.status >= 400 && response.status < 500 && response.status !== 429) {
      throw new ApiError(response.status, detail);
    }

    lastError = new ApiError(response.status, detail);

    // If retryable and not last attempt, continue loop
    if (!RETRYABLE_STATUS_CODES.has(response.status) || attempt >= MAX_RETRIES) {
      throw lastError;
    }
  }

  throw lastError ?? new ApiError(0, "Unknown error");
}
