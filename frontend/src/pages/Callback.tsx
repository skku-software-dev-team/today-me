import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

interface Props {
  onCallback: (token: string) => void;
}

export default function Callback({ onCallback }: Props) {
  const navigate = useNavigate();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("access_token");

    if (token) {
      onCallback(token);
      navigate("/", { replace: true });
    } else {
      navigate("/login", { replace: true });
    }
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-stone-50">
      <p className="text-stone-500 text-sm">로그인 중...</p>
    </div>
  );
}
