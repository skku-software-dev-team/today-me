import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./hooks/useAuth";
import Login from "./pages/Login";
import Callback from "./pages/Callback";
import Home from "./pages/Home";
import Result from "./pages/Result";
import History from "./pages/History";

export default function App() {
  const { state, login, logout, onCallback } = useAuth();

  if (state === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-stone-50">
        <div className="w-5 h-5 border-2 border-stone-300 border-t-stone-600 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={
            state === "authenticated"
              ? <Navigate to="/" replace />
              : <Login onLogin={login} />
          }
        />
        <Route path="/callback" element={<Callback onCallback={onCallback} />} />
        <Route
          path="/"
          element={state === "authenticated" ? <Home onLogout={logout} /> : <Navigate to="/login" replace />}
        />
        <Route
          path="/result"
          element={state === "authenticated" ? <Result /> : <Navigate to="/login" replace />}
        />
        <Route
          path="/history"
          element={state === "authenticated" ? <History /> : <Navigate to="/login" replace />}
        />
      </Routes>
    </BrowserRouter>
  );
}
