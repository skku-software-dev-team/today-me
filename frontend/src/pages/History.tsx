import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getHistory } from "../lib/api";
import type { HistoryReport } from "../types";

function EnergyDots({ energy }: { energy: number }) {
  return (
    <span className="text-stone-300 tracking-tight text-xs select-none">
      {"●".repeat(energy)}
      {"○".repeat(5 - energy)}
    </span>
  );
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("ko-KR", {
    month: "long",
    day: "numeric",
    weekday: "short",
  });
}

export default function History() {
  const navigate = useNavigate();
  const [reports, setReports] = useState<HistoryReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    getHistory()
      .then((r) => setReports(r.reports))
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-stone-50">
      <header className="flex items-center px-6 py-4 border-b border-stone-100 bg-white">
        <button
          onClick={() => navigate("/")}
          className="text-sm text-stone-500 hover:text-stone-800 transition-colors w-16"
        >
          ← 돌아가기
        </button>
        <h2 className="flex-1 text-center text-sm font-medium text-stone-700">
          나의 히스토리
        </h2>
        <div className="w-16" />
      </header>

      <main className="max-w-md mx-auto px-6 py-6">
        {loading && (
          <div className="flex justify-center py-16">
            <div className="w-5 h-5 border-2 border-stone-300 border-t-stone-600 rounded-full animate-spin" />
          </div>
        )}

        {error && (
          <p className="text-center text-stone-400 text-sm py-16">
            불러오는 데 실패했어요.
          </p>
        )}

        {!loading && !error && reports.length === 0 && (
          <div className="text-center py-16">
            <p className="text-stone-400 text-sm">아직 기록이 없어요.</p>
            <button
              onClick={() => navigate("/")}
              className="mt-3 text-sm text-stone-600 underline underline-offset-2"
            >
              첫 번째 리포트 만들기
            </button>
          </div>
        )}

        {!loading && !error && reports.length > 0 && (
          <div className="flex flex-col gap-3">
            {reports.map((r: HistoryReport) => (
              <div
                key={r.report_id}
                className="bg-white rounded-xl border border-stone-100 overflow-hidden flex"
              >
                {r.moodboard_url ? (
                  <img
                    src={r.moodboard_url}
                    alt=""
                    className="w-20 h-20 object-cover flex-shrink-0"
                  />
                ) : (
                  <div className="w-20 h-20 bg-stone-100 flex-shrink-0" />
                )}
                <div className="px-4 py-3 flex flex-col justify-between min-w-0 flex-1">
                  <p className="text-sm text-stone-800 line-clamp-2 leading-snug">
                    {r.mood}
                  </p>
                  <div className="flex items-center gap-2 mt-1.5">
                    <span className="text-xs text-stone-400">{r.weather}</span>
                    <EnergyDots energy={r.energy} />
                  </div>
                  <p className="text-xs text-stone-300 mt-1">
                    {formatDate(r.created_at)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
