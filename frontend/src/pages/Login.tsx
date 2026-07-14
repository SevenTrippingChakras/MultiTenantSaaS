import { useState, type FormEvent } from "react";
import { Flame } from "lucide-react";
import { authenticate } from "./Login.helper";

interface LoginProps {
  onAuthed: () => void;
}

export default function Login({ onAuthed }: LoginProps) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await authenticate(mode, email, password);
      onAuthed();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex h-screen items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="flex size-16 items-center justify-center rounded-2xl bg-gradient-to-br from-ember to-[#ff6f2a] shadow-xl shadow-ember/30">
            <Flame className="float-y size-8 text-[#2a1400]" />
          </div>
          <h1 className="mt-3 text-4xl font-bold tracking-tight">AIchat</h1>
          <p className="text-muted-foreground">your fireside companion</p>
        </div>

        <form onSubmit={submit} className="glass flex flex-col gap-4 rounded-2xl p-7">
          <p className="text-lg font-semibold">
            {mode === "login" ? "Welcome back" : "Create your account"}
          </p>

          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="h-11 rounded-xl border border-white/15 bg-white/5 px-4 text-foreground placeholder:text-muted-foreground focus:border-moss/60 focus:outline-none focus:ring-2 focus:ring-moss/30"
          />
          <input
            type="password"
            placeholder="Password (min 8 chars)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            required
            className="h-11 rounded-xl border border-white/15 bg-white/5 px-4 text-foreground placeholder:text-muted-foreground focus:border-moss/60 focus:outline-none focus:ring-2 focus:ring-moss/30"
          />

          {error && (
            <div className="rounded-xl border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm font-medium text-destructive">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={busy}
            className="rounded-xl bg-gradient-to-r from-ember to-[#ff6f2a] py-2.5 font-bold text-[#2a1400] shadow-lg shadow-ember/25 transition hover:brightness-105 active:scale-[0.98] disabled:opacity-50"
          >
            {busy ? "…" : mode === "login" ? "Sign in" : "Sign up"}
          </button>

          <button
            type="button"
            className="text-sm font-medium text-muted-foreground transition hover:text-moss"
            onClick={() => setMode(mode === "login" ? "register" : "login")}
          >
            {mode === "login"
              ? "Need an account? Sign up"
              : "Have an account? Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
