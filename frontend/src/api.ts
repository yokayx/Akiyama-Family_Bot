export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    credentials: "same-origin",
    ...init,
    headers: init.body instanceof FormData ? init.headers : {
      "Content-Type": "application/json",
      ...(init.headers as Record<string, string> | undefined),
    },
  });
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const body = JSON.parse(text);
      message = body.error || body.detail || message;
    } catch {
      // non-JSON error body
    }
    throw new ApiError(message, response.status);
  }
  return text ? (JSON.parse(text) as T) : (undefined as T);
}
