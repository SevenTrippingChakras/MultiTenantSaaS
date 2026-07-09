import { useEffect, useState } from "react";
import { Flame } from "lucide-react";
import Login from "./pages/Login";
import Chat from "./pages/Chat";
import BackgroundFX from "./components/BackgroundFX";
import { getMe } from "./api";
import { clearToken, getToken } from "./token";

export default function App() {
  const [authed, setAuthed] = useState(false);
  const [loading, setLoading] = useState(true);

  // On load, verify any stored token is still valid.
  useEffect(() => {
    async function check() {
      if (!getToken()) return setLoading(false);
      try {
        await getMe();
        setAuthed(true);
      } catch {
        clearToken();
      } finally {
        setLoading(false);
      }
    }
    check();
  }, []);

  function logout() {
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
