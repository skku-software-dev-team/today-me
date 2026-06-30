import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { curate, geocode, reverseGeocode, fetchWeather } from "../lib/api";

const ENERGY_LABELS: Record<number, string> = {
  1: "완전 방전",
  2: "피곤함",
  3: "보통",
  4: "활기참",
  5: "최고조",
};

// Seoul city center as fallback when user skips location
const SEOUL_DEFAULT = { lat: 37.5665, lng: 126.978 };

type LocState = "idle" | "detecting" | "gps" | "text";

interface Props {
  onLogout: () => void;
}

export default function Home({ onLogout }: Props) {
  const navigate = useNavigate();
  const [mood, setMood] = useState("");
  const [energy, setEnergy] = useState(3);
  const [locState, setLocState] = useState<LocState>("idle");
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(
    null,
  );
  const [locationName, setLocationName] = useState<string | null>(null);
  const [weatherInfo, setWeatherInfo] = useState<{
    emoji: string;
    label: string;
    temp: number;
  } | null>(null);
  const [locationText, setLocationText] = useState("");
  const [locGeocoding, setLocGeocoding] = useState(false);
  const [locTextError, setLocTextError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function detectGps() {
    setLocState("detecting");
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const { latitude: lat, longitude: lng } = pos.coords;
        setCoords({ lat, lng });
        setLocState("gps");
        const [name, weather] = await Promise.all([
          reverseGeocode(lat, lng),
          fetchWeather(lat, lng),
        ]);
        setLocationName(name);
        setWeatherInfo(weather);
      },
      () => setLocState("text"),
    );
  }

  function resetLocation() {
    setLocState("idle");
    setCoords(null);
    setLocationName(null);
    setWeatherInfo(null);
    setLocationText("");
    setLocTextError(null);
  }

  async function confirmTextLocation() {
    if (!locationText.trim()) return;
    setLocGeocoding(true);
    setLocTextError(null);
    const result = await geocode(locationText);
    if (!result) {
      setLocTextError("위치를 찾을 수 없어요. 다른 이름으로 입력해보세요.");
      setLocGeocoding(false);
      return;
    }
    setCoords(result);
    setLocationName(locationText.trim());
    setLocState("gps");
    const weather = await fetchWeather(result.lat, result.lng);
    setWeatherInfo(weather);
    setLocGeocoding(false);
  }

  async function handleSubmit() {
    if (!mood.trim()) {
      setError("오늘 기분을 입력해주세요.");
      return;
    }

    let location = coords;

    if (!location && locState === "text") {
      if (!locationText.trim()) {
        setError("위치를 입력해주세요.");
        return;
      }
      location = await geocode(locationText);
      if (!location) {
        setError("위치를 찾을 수 없어요. 다른 이름으로 입력해보세요.");
        return;
      }
    }

    setSubmitting(true);
    setError(null);
    try {
      const finalLocation = location ?? SEOUL_DEFAULT;
      const weather =
        weatherInfo ??
        (await fetchWeather(finalLocation.lat, finalLocation.lng));
      const result = await curate({
        mood,
        weather: weather?.label ?? "",
        energy,
        location: finalLocation,
      });
      navigate("/result", { state: result });
    } catch {
      setError("오류가 발생했어요. 잠시 후 다시 시도해주세요.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-stone-50">
      <header className="flex items-center justify-between px-6 py-4 border-b border-stone-100 bg-white">
        <h1 className="text-base font-semibold text-stone-800">오늘의 나</h1>
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate("/history")}
            className="text-sm text-stone-500 hover:text-stone-800 transition-colors"
          >
            히스토리
          </button>
          <button
            onClick={onLogout}
            className="text-sm text-stone-400 hover:text-stone-600 transition-colors"
          >
            로그아웃
          </button>
        </div>
      </header>

      <main className="max-w-md mx-auto px-6 py-10 flex flex-col gap-8">
        {/* Mood */}
        <section>
          <label className="block text-sm font-medium text-stone-700 mb-2">
            오늘 기분이 어때요?
          </label>
          <div className="relative">
            <textarea
              value={mood}
              onChange={(e) => setMood(e.target.value.slice(0, 200))}
              placeholder="예) 왠지 모르게 울적하고 비가 와서 집에 있고 싶은 날"
              rows={4}
              className="w-full resize-none rounded-xl border border-stone-200 bg-white px-4 py-3 pr-12 text-sm text-stone-800 placeholder-stone-300 focus:outline-none focus:ring-2 focus:ring-stone-300"
            />
            <span className="absolute bottom-3 right-3 text-xs text-stone-300 select-none">
              {mood.length}/200
            </span>
          </div>
        </section>

        {/* Energy */}
        <section>
          <label className="block text-sm font-medium text-stone-700 mb-3">
            에너지 레벨
          </label>
          <div className="flex gap-2">
            {[1, 2, 3, 4, 5].map((e) => (
              <button
                key={e}
                onClick={() => setEnergy(e)}
                className={`flex-1 py-3 rounded-xl text-sm font-medium transition-all ${
                  energy === e
                    ? "bg-stone-800 text-white shadow-sm"
                    : "bg-white border border-stone-200 text-stone-500 hover:border-stone-400"
                }`}
              >
                {e}
              </button>
            ))}
          </div>
          <p className="mt-2 text-xs text-stone-400 text-center">
            {ENERGY_LABELS[energy]}
          </p>
        </section>

        {/* Location */}
        <section>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-stone-700">위치</label>
            <span className="text-xs text-stone-400">추천 품질을 높여줘요</span>
          </div>

          {locState === "idle" && (
            <div className="flex flex-col gap-2">
              <button
                onClick={detectGps}
                className="w-full py-3 rounded-xl border border-dashed border-stone-300 text-sm text-stone-500 hover:border-stone-500 hover:text-stone-700 transition-colors"
              >
                📍 현재 위치 자동 감지
              </button>
              <button
                onClick={() => setLocState("text")}
                className="text-xs text-stone-400 underline underline-offset-2 text-center"
              >
                직접 입력하기
              </button>
            </div>
          )}

          {locState === "detecting" && (
            <div className="flex items-center justify-center py-3 gap-2 text-sm text-stone-400">
              <div className="w-4 h-4 border-2 border-stone-300 border-t-stone-500 rounded-full animate-spin" />
              위치 감지 중...
            </div>
          )}

          {locState === "gps" && (
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between rounded-xl border border-stone-200 bg-white px-4 py-3">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="flex-shrink-0">📍</span>
                  <span className="text-sm text-stone-600 truncate">
                    {locationName ?? "현재 위치 확인됨"}
                  </span>
                </div>
                <button
                  onClick={resetLocation}
                  className="text-xs text-stone-400 hover:text-stone-600 flex-shrink-0 ml-3"
                >
                  변경
                </button>
              </div>
              {weatherInfo && (
                <p className="text-sm text-stone-500 px-1">
                  {weatherInfo.emoji} 지금 {weatherInfo.label},{" "}
                  {weatherInfo.temp}°C예요!
                </p>
              )}
            </div>
          )}

          {locState === "text" && (
            <div className="flex flex-col gap-1.5">
              <div className="flex gap-2">
                <input
                  value={locationText}
                  onChange={(e) => {
                    setLocationText(e.target.value);
                    setLocTextError(null);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") confirmTextLocation();
                  }}
                  placeholder="예) 강남구, 홍대, 마포구"
                  disabled={locGeocoding}
                  className="flex-1 rounded-xl border border-stone-200 bg-white px-4 py-3 text-sm text-stone-800 placeholder-stone-300 focus:outline-none focus:ring-2 focus:ring-stone-300 disabled:opacity-50"
                />
                <button
                  onClick={confirmTextLocation}
                  disabled={!locationText.trim() || locGeocoding}
                  className="px-4 rounded-xl bg-stone-800 text-white text-sm font-medium disabled:opacity-40 flex items-center gap-1.5 flex-shrink-0"
                >
                  {locGeocoding ? (
                    <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                  ) : (
                    "확인"
                  )}
                </button>
              </div>
              <div className="flex items-center justify-between px-1">
                {locTextError ? (
                  <p className="text-xs text-red-500">{locTextError}</p>
                ) : (
                  <p className="text-xs text-stone-400">
                    GPS 권한이 없어 직접 입력해주세요.
                  </p>
                )}
                <button
                  onClick={resetLocation}
                  className="text-xs text-stone-400 underline underline-offset-2"
                >
                  취소
                </button>
              </div>
            </div>
          )}
        </section>

        {error && <p className="text-sm text-red-500 -mt-2">{error}</p>}

        <button
          onClick={handleSubmit}
          disabled={submitting || !mood.trim()}
          className="w-full py-4 rounded-xl bg-stone-800 text-white text-sm font-medium disabled:opacity-40 hover:bg-stone-700 active:scale-95 transition-all"
        >
          {submitting ? (
            <span className="flex items-center justify-center gap-2">
              <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
              큐레이션 중...
            </span>
          ) : (
            "오늘의 나 만들기"
          )}
        </button>
      </main>
    </div>
  );
}
