let accessToken: string | null = null;

export function setAccessToken(token: string) {
  accessToken = token;
}

export function getAccessToken() {
  return accessToken;
}

export function clearAccessToken() {
  accessToken = null;
}

// refresh_token 쿠키로 access_token 재발급
export async function refreshAccessToken(): Promise<string | null> {
  const res = await fetch("/auth/refresh", { method: "POST", credentials: "include" });
  if (!res.ok) return null;
  const { access_token } = await res.json();
  setAccessToken(access_token);
  return access_token;
}

export async function apiFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const token = accessToken ?? await refreshAccessToken();
  if (!token) throw new Error("Unauthenticated");

  const res = await fetch(input, {
    ...init,
    credentials: "include",
    headers: { ...init.headers, Authorization: `Bearer ${token}` },
  });

  if (res.status === 401) {
    const newToken = await refreshAccessToken();
    if (!newToken) throw new Error("Unauthenticated");
    return fetch(input, {
      ...init,
      credentials: "include",
      headers: { ...init.headers, Authorization: `Bearer ${newToken}` },
    });
  }

  return res;
}
