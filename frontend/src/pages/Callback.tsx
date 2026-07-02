import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

interface Props {
  onCallback: (token: string) => void;
}

export default function Callback({ onCallback }: Props) {
  const navigate = useNavigate();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");

    if (!code) {
      navigate("/login", { replace: true });
      return;
    }

    fetch(`/api/auth/token?code=${encodeURIComponent(code)}`, {
      method: "POST",
      credentials: "include",
    })
      .then((res) => {
        if (!res.ok) throw new Error("token exchange failed");
        return res.json();
      })
      .then(({ access_token }) => {
        onCallback(access_token);
        navigate("/", { replace: true });
      })
      .catch(() => navigate("/login", { replace: true }));
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-stone-50">
      <p className="text-stone-500 text-sm">로그인 중...</p>
    </div>
  );
}
