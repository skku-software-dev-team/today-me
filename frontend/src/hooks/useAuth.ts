import { useEffect, useState } from "react";
import {
  refreshAccessToken,
  setAccessToken,
  clearAccessToken,
} from "../lib/api";

export type AuthState = "loading" | "authenticated" | "unauthenticated";

export function useAuth() {
  const [state, setState] = useState<AuthState>("loading");

  useEffect(() => {
    refreshAccessToken().then((token) => {
      setState(token ? "authenticated" : "unauthenticated");
    });
  }, []);

  function login() {
    window.location.href = "/api/auth/google";
  }

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
    clearAccessToken();
    setState("unauthenticated");
  }

  function onCallback(token: string) {
    setAccessToken(token);
    setState("authenticated");
  }

  return { state, login, logout, onCallback };
}
