import { API_URL } from "./config";
import { clearToken, getToken, setToken } from "./token";
import type { Message, Session, TokenResponse, User } from "./types";

interface RequestOptions {
  method?: string;
  body?: unknown;
  // Cookie-authed POSTs (logout) must echo the CSRF cookie in a header.
  csrf?: boolean;
  // Whether a 401 should trigger a silent refresh + one retry. Off for the
  // auth endpoints, where a 401 is a real credential failure.
  retryAuth?: boolean;
}

/** Read a non-httpOnly cookie (the CSRF token) by name. */
function readCookie(name: string): string | null {
  const m = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return m ? decodeURIComponent(m[1]) : null;
}

function buildHeaders(opts: RequestOptions): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (opts.csrf) {
    const csrf = readCookie("csrf_token");
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }
  return headers;
}

let refreshInFlight: Promise<boolean> | null = null;

/** Trade the refresh cookie for a fresh access token. Returns success.
 *
 * Single-flight: concurrent callers (e.g. several requests that 401 at once, or
 * React StrictMode double-invoking an effect) share one in-flight refresh. Each
 * refresh rotates the token, so firing several at once would make the later ones
 * look like a replay and trip server-side reuse detection, killing the session.
 */
export function refreshAccessToken(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = doRefresh().finally(() => {
      refreshInFlight = null;
    });
  }
  return refreshInFlight;
}

async function doRefresh(): Promise<boolean> {
  const csrf = readCookie("csrf_token");
  const res = await fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    credentials: "include",
    headers: csrf ? { "X-CSRF-Token": csrf } : {},
  });
  if (!res.ok) {
    clearToken();
    return false;
  }
  const data: TokenResponse = await res.json();
  setToken(data.access_token);
  return true;
}

function send(path: string, opts: RequestOptions): Promise<Response> {
  return fetch(`${API_URL}${path}`, {
    method: opts.method ?? "GET",
    headers: buildHeaders(opts),
    body: opts.body ? JSON.stringify(opts.body) : undefined,
    credentials: "include",
  });
}

async function parse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.error?.message || `Request failed: ${res.status}`);
  }
  return res.status === 204 ? (null as T) : res.json();
}

// Core request helper: attaches the JWT, and on a 401 silently refreshes the
// access token and retries the request once.
async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  let res = await send(path, opts);
  if (res.status === 401 && opts.retryAuth !== false && (await refreshAccessToken())) {
    res = await send(path, opts);
  }
  return parse<T>(res);
}

// --- Auth ---
export const register = (email: string, password: string) =>
  request<User>("/auth/register", {
    method: "POST",
    body: { email, password },
    retryAuth: false,
  });

export const login = (email: string, password: string) =>
  request<TokenResponse>("/auth/login", {
    method: "POST",
    body: { email, password },
    retryAuth: false,
  });

export const logout = () =>
  request<null>("/auth/logout", { method: "POST", csrf: true, retryAuth: false });

export const getMe = () => request<User>("/auth/me");

// --- Sessions ---
export const listSessions = () => request<Session[]>("/sessions");
export const createSession = (title: string | null) =>
  request<Session>("/sessions", { method: "POST", body: { title } });
export const deleteSession = (id: string) =>
  request<null>(`/sessions/${id}`, { method: "DELETE" });
export const getMessages = (id: string) =>
  request<Message[]>(`/sessions/${id}/messages`);

// --- Chat (SSE streaming over fetch) ---
function streamFetch(
  sessionId: string,
  content: string,
  signal?: AbortSignal,
): Promise<Response> {
  return fetch(`${API_URL}/chat/${sessionId}`, {
    method: "POST",
    headers: buildHeaders({ body: content }),
    body: JSON.stringify({ content }),
    credentials: "include",
    signal,
  });
}

function isAbort(e: unknown): boolean {
  return e instanceof DOMException && e.name === "AbortError";
}

interface StreamOptions {
  // The server sends a generation id as its first event; the UI keeps it so it
  // can call stopChat() to cancel this stream server-side.
  onGenerationId?: (id: string) => void;
  // Aborting stops reading and closes the connection (which the server also
  // treats as a stop). An abort resolves the promise normally, not as an error.
  signal?: AbortSignal;
}

// Calls onToken(delta) for each token; resolves when the stream ends (or aborts).
export async function streamChat(
  sessionId: string,
  content: string,
  onToken: (delta: string) => void,
  opts: StreamOptions = {},
): Promise<void> {
  let res: Response;
  try {
    res = await streamFetch(sessionId, content, opts.signal);
    if (res.status === 401 && (await refreshAccessToken())) {
      res = await streamFetch(sessionId, content, opts.signal);
    }
  } catch (e) {
    if (isAbort(e)) return;
    throw e;
  }
  if (!res.ok || !res.body) throw new Error(`Chat failed: ${res.status}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // SSE frames are separated by a blank line. Heartbeat comments (": ping")
      // don't start with "data:", so they're skipped.
      const frames = buffer.split("\n\n");
      buffer = frames.pop() ?? "";

      for (const frame of frames) {
        const line = frame.trim();
        if (!line.startsWith("data:")) continue;
        const obj = JSON.parse(line.slice(5).trim());
        if (obj.generation_id) {
          opts.onGenerationId?.(obj.generation_id);
          continue;
        }
        if (obj.error) throw new Error(obj.error);
        if (obj.done) return;
        if (obj.delta) onToken(obj.delta);
      }
    }
  } catch (e) {
    if (isAbort(e)) return;
    throw e;
  }
}

// Cancel an in-flight stream server-side so we stop paying for tokens.
export const stopChat = (sessionId: string, generationId: string) =>
  request<{ stopped: boolean }>(`/chat/${sessionId}/stop/${generationId}`, {
    method: "POST",
  });
