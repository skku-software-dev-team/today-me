import type { CurateResponse, HistoryResponse, AgentKey } from "../types";

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
  const res = await fetch("/api/auth/refresh", {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) return null;
  const { access_token } = await res.json();
  setAccessToken(access_token);
  return access_token;
}

export async function apiFetch(
  input: string,
  init: RequestInit = {},
): Promise<Response> {
  const token = accessToken ?? (await refreshAccessToken());
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

export async function curate(payload: {
  mood: string;
  energy: number;
  location: { lat: number; lng: number };
}): Promise<CurateResponse> {
  const res = await apiFetch("/v1/curate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("curate failed");
  return res.json();
}

export async function submitFeedback(payload: {
  report_id: string;
  agent: AgentKey;
  pick_index: number;
  score: 1 | -1;
  comment?: string;
}): Promise<void> {
  await apiFetch("/v1/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function getHistory(
  limit = 20,
  offset = 0,
): Promise<HistoryResponse> {
  const res = await apiFetch(`/v1/history?limit=${limit}&offset=${offset}`);
  if (!res.ok) throw new Error("history failed");
  return res.json();
}

const WMO_WEATHER: Record<number, { emoji: string; label: string }> = {
  0: { emoji: "☀️", label: "맑아요" },
  1: { emoji: "🌤️", label: "대체로 맑아요" },
  2: { emoji: "⛅", label: "구름이 조금 있어요" },
  3: { emoji: "☁️", label: "흐려요" },
  45: { emoji: "🌫️", label: "안개가 끼었어요" },
  48: { emoji: "🌫️", label: "안개가 짙어요" },
  51: { emoji: "🌦️", label: "이슬비가 내려요" },
  53: { emoji: "🌦️", label: "이슬비가 내려요" },
  55: { emoji: "🌧️", label: "이슬비가 제법 내려요" },
  61: { emoji: "🌧️", label: "비가 내려요" },
  63: { emoji: "🌧️", label: "비가 꽤 내려요" },
  65: { emoji: "🌧️", label: "비가 많이 내려요" },
  71: { emoji: "🌨️", label: "눈이 내려요" },
  73: { emoji: "🌨️", label: "눈이 꽤 내려요" },
  75: { emoji: "❄️", label: "눈이 많이 내려요" },
  77: { emoji: "🌨️", label: "눈발이 날려요" },
  80: { emoji: "🌦️", label: "소나기가 내려요" },
  81: { emoji: "🌧️", label: "소나기가 꽤 내려요" },
  82: { emoji: "⛈️", label: "소나기가 심해요" },
  95: { emoji: "⛈️", label: "천둥번개가 쳐요" },
  96: { emoji: "⛈️", label: "우박을 동반한 번개가 쳐요" },
  99: { emoji: "⛈️", label: "심한 폭풍이에요" },
};

export async function fetchWeather(
  lat: number,
  lng: number,
): Promise<{ emoji: string; label: string; temp: number } | null> {
  try {
    const res = await fetch(
      `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lng}&current=weather_code,temperature_2m&timezone=auto`,
    );
    const data = await res.json();
    const code: number = data.current.weather_code;
    const temp: number = Math.round(data.current.temperature_2m);
    const info = WMO_WEATHER[code] ?? {
      emoji: "🌡️",
      label: "날씨 정보를 확인했어요",
    };
    return { ...info, temp };
  } catch {
    return null;
  }
}

export async function reverseGeocode(
  lat: number,
  lng: number,
): Promise<string | null> {
  try {
    const res = await fetch(
      `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json`,
      { headers: { "Accept-Language": "ko" } },
    );
    const data = await res.json();
    const { suburb, city_district, county, city, town, village } =
      data.address ?? {};
    const district = city_district ?? county ?? "";
    const neighbourhood = suburb ?? "";
    const cityName = city ?? town ?? village ?? "";
    return (
      [cityName, district, neighbourhood].filter(Boolean).join(" ") || null
    );
  } catch {
    return null;
  }
}

export async function geocode(
  query: string,
): Promise<{ lat: number; lng: number } | null> {
  try {
    const res = await fetch(
      `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&format=json&limit=1&countrycodes=kr`,
      { headers: { "Accept-Language": "ko" } },
    );
    const data = await res.json();
    if (!data.length) return null;
    return { lat: parseFloat(data[0].lat), lng: parseFloat(data[0].lon) };
  } catch {
    return null;
  }
}
