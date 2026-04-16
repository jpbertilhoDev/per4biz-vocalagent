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

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_URL}${path}`;
  const response = await fetch(url, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // body não é JSON — mantém statusText
    }
    // 401 — redirecionar para login (re-auth)
    if (response.status === 401 && typeof window !== "undefined") {
      window.location.href = "/";
    }
    throw new ApiError(response.status, detail);
  }

  return response.json();
}
