import { useEffect, useState } from "react";
import { Flame } from "lucide-react";
import Login from "./pages/Login";
import Chat from "./pages/Chat";
import BackgroundFX from "./components/BackgroundFX";
import { logout as apiLogout, refreshAccessToken } from "./api";
import { clearToken } from "./token";

export default function App() {
  const [authed, setAuthed] = useState(false);
  const [loading, setLoading] = useState(true);

  // On load the in-memory access token is gone, so try a silent refresh: if the
  // httpOnly refresh cookie is still valid, we get a new access token back.
  useEffect(() => {
    async function check() {
      if (await refreshAccessToken()) setAuthed(true);
      setLoading(false);
    }
    check();
  }, []);

  async function logout() {
    try {
      await apiLogout();
    } catch {
      // Best effort: still clear local state even if the request fails.
    }
    clearToken();
    setAuthed(false);
  }

  return (
    <>
      <BackgroundFX />
      {loading ? (
        <div className="flex h-screen flex-col items-center justify-center gap-3 text-muted-foreground">
          <Flame className="float-y size-12 text-ember" />
          <span className="text-lg">Loading…</span>
        </div>
      ) : !authed ? (
        <Login onAuthed={() => setAuthed(true)} />
      ) : (
        <Chat onLogout={logout} />
      )}
    </>
  );
}
