interface Props {
  onLogout: () => void;
}

export default function Home({ onLogout }: Props) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-stone-50">
      <div className="flex flex-col items-center gap-6 text-center">
        <h1 className="text-3xl font-bold text-stone-800">안녕하세요 👋</h1>
        <p className="text-stone-500 text-sm">로그인 성공!</p>
        <button
          onClick={onLogout}
          className="px-4 py-2 text-sm text-stone-600 border border-stone-200 rounded-lg hover:bg-stone-100 transition-colors"
        >
          로그아웃
        </button>
      </div>
    </div>
  );
}
