const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

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

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_URL}${path}`;

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

    // 401 — redirecionar para login (re-auth) — never retry
    if (response.status === 401 && typeof window !== "undefined") {
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
