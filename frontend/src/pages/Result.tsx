import { useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { submitFeedback } from "../lib/api";
import type {
  CurateResponse,
  AgentKey,
  MusicPick,
  PlacePick,
  FoodPick,
  StylePick,
} from "../types";

interface FeedbackBtnsProps {
  feedbackKey: string;
  ratings: Record<string, 1 | -1>;
  onRate: (score: 1 | -1, comment?: string) => void;
}

function FeedbackBtns({ feedbackKey, ratings, onRate }: FeedbackBtnsProps) {
  const rating = ratings[feedbackKey];
  const [open, setOpen] = useState(false);
  const [comment, setComment] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  function handleScore(score: 1 | -1) {
    onRate(score);
    setOpen(true);
    setTimeout(() => inputRef.current?.focus(), 50);
  }

  function handleSend() {
    if (comment.trim()) onRate(rating!, comment.trim());
    setOpen(false);
    setComment("");
  }

  function handleSkip() {
    setOpen(false);
    setComment("");
  }

  return (
    <div className="mt-3 pt-3 border-t border-stone-50">
      <div className="flex gap-1.5">
        <button
          onClick={() => handleScore(1)}
          className={`px-3 py-1 rounded-full text-xs transition-colors ${
            rating === 1
              ? "bg-emerald-100 text-emerald-700"
              : "text-stone-400 hover:bg-stone-100"
          }`}
        >
          👍
        </button>
        <button
          onClick={() => handleScore(-1)}
          className={`px-3 py-1 rounded-full text-xs transition-colors ${
            rating === -1
              ? "bg-red-100 text-red-600"
              : "text-stone-400 hover:bg-stone-100"
          }`}
        >
          👎
        </button>
      </div>

      {open && rating && (
        <div className="mt-2 flex items-center gap-2">
          <input
            ref={inputRef}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSend();
              if (e.key === "Escape") handleSkip();
            }}
            placeholder="어떤 점이 좋았나요? (선택)"
            className="flex-1 text-xs rounded-lg border border-stone-200 px-3 py-1.5 text-stone-700 placeholder-stone-300 focus:outline-none focus:ring-1 focus:ring-stone-300"
          />
          {comment.trim() && (
            <button
              onClick={handleSend}
              className="text-xs text-stone-500 hover:text-stone-800 px-2 flex-shrink-0"
            >
              전송
            </button>
          )}
          <button
            onClick={handleSkip}
            className="text-xs text-stone-300 hover:text-stone-500 flex-shrink-0"
          >
            건너뛰기
          </button>
        </div>
      )}
    </div>
  );
}

export default function Result() {
  const location = useLocation();
  const navigate = useNavigate();
  const result = location.state as CurateResponse | null;
  const [ratings, setRatings] = useState<Record<string, 1 | -1>>({});

  if (!result) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-stone-50">
        <p className="text-stone-500 text-sm">결과를 찾을 수 없어요.</p>
        <button
          onClick={() => navigate("/")}
          className="text-sm text-stone-600 underline underline-offset-2"
        >
          처음으로 돌아가기
        </button>
      </div>
    );
  }

  function rate(
    agent: AgentKey,
    index: number,
    score: 1 | -1,
    comment?: string,
  ) {
    const key = `${agent}-${index}`;
    setRatings((prev) => ({ ...prev, [key]: score }));
    submitFeedback({
      report_id: result!.report_id,
      agent,
      pick_index: index,
      score,
      comment,
    }).catch(() => {});
  }

  return (
    <div className="min-h-screen bg-stone-50">
      <header className="flex items-center justify-between px-6 py-4 border-b border-stone-100 bg-white">
        <button
          onClick={() => navigate("/")}
          className="text-sm text-stone-500 hover:text-stone-800 transition-colors"
        >
          ← 다시 하기
        </button>
        <button
          onClick={() => navigate("/history")}
          className="text-sm text-stone-500 hover:text-stone-800 transition-colors"
        >
          히스토리
        </button>
      </header>

      <main className="max-w-md mx-auto pb-12">
        {/* Moodboard */}
        {result.moodboard_url && (
          <img
            src={result.moodboard_url}
            alt="오늘의 무드보드"
            className="w-full aspect-video object-cover"
          />
        )}

        <div className="px-6 pt-6 flex flex-col gap-8">
          {/* Music */}
          <section>
            <h2 className="text-xs font-semibold uppercase tracking-widest text-stone-400 mb-3">
              음악
            </h2>
            <div className="flex flex-col gap-3">
              {result.music_picks.map((p: MusicPick, i) => (
                <div
                  key={i}
                  className="bg-white rounded-xl p-4 border border-stone-100"
                >
                  <a
                    href={p.youtube_url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-start gap-3 group"
                  >
                    <span className="text-lg mt-0.5 flex-shrink-0">🎵</span>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-stone-800 group-hover:underline truncate">
                        {p.title}
                      </p>
                      <p className="text-xs text-stone-400 mt-0.5">
                        {p.artist}
                      </p>
                    </div>
                  </a>
                  <FeedbackBtns
                    feedbackKey={`music-${i}`}
                    ratings={ratings}
                    onRate={(score, comment) =>
                      rate("music", i, score, comment)
                    }
                  />
                </div>
              ))}
            </div>
          </section>

          {/* Place */}
          <section>
            <h2 className="text-xs font-semibold uppercase tracking-widest text-stone-400 mb-3">
              장소
            </h2>
            <div className="flex flex-col gap-3">
              {result.place_picks.map((p: PlacePick, i) => (
                <div
                  key={i}
                  className="bg-white rounded-xl p-4 border border-stone-100"
                >
                  <a
                    href={p.maps_url}
                    target="_blank"
                    rel="noreferrer"
                    className="group"
                  >
                    <p className="text-sm font-medium text-stone-800 group-hover:underline">
                      📍 {p.name}
                    </p>
                    <p className="text-xs text-stone-400 mt-0.5">{p.address}</p>
                  </a>
                  <p className="text-xs text-stone-500 mt-2 leading-relaxed">
                    {p.reason}
                  </p>
                  <FeedbackBtns
                    feedbackKey={`place-${i}`}
                    ratings={ratings}
                    onRate={(score, comment) =>
                      rate("place", i, score, comment)
                    }
                  />
                </div>
              ))}
            </div>
          </section>

          {/* Food */}
          <section>
            <h2 className="text-xs font-semibold uppercase tracking-widest text-stone-400 mb-3">
              맛집
            </h2>
            <div className="flex flex-col gap-3">
              {result.food_picks.map((p: FoodPick, i) => (
                <div
                  key={i}
                  className="bg-white rounded-xl p-4 border border-stone-100"
                >
                  <p className="text-sm font-medium text-stone-800">
                    🍽 {p.name}
                  </p>
                  <p className="text-xs text-stone-400 mt-0.5">
                    {p.cuisine} · {p.address}
                  </p>
                  <p className="text-xs text-stone-500 mt-2 leading-relaxed">
                    {p.reason}
                  </p>
                  <FeedbackBtns
                    feedbackKey={`food-${i}`}
                    ratings={ratings}
                    onRate={(score, comment) => rate("food", i, score, comment)}
                  />
                </div>
              ))}
            </div>
          </section>

          {/* Style */}
          <section>
            <h2 className="text-xs font-semibold uppercase tracking-widest text-stone-400 mb-3">
              스타일
            </h2>
            <div className="flex flex-col gap-3">
              {result.style_picks.map((p: StylePick, i) => (
                <div
                  key={i}
                  className="bg-white rounded-xl p-4 border border-stone-100"
                >
                  <p className="text-sm font-medium text-stone-800">
                    👗 {p.description}
                  </p>
                  <p className="text-xs text-stone-500 mt-2 leading-relaxed">
                    {p.reason}
                  </p>
                  <FeedbackBtns
                    feedbackKey={`style-${i}`}
                    ratings={ratings}
                    onRate={(score, comment) =>
                      rate("style", i, score, comment)
                    }
                  />
                </div>
              ))}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
