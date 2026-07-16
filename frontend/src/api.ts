import axios, { type AxiosError, type AxiosResponse } from "axios";
import { API_URL, MESSAGE_PAGE_SIZE, SESSION_PAGE_SIZE } from "./config";
import { clearToken, getToken, setToken } from "./token";
import type {
  CheckoutResponse,
  ExportResponse,
  Message,
  Page,
  PlansResponse,
  Session,
  TokenResponse,
  UsageResponse,
  User,
} from "./types";

// Per-request flags we read back in the interceptors.
declare module "axios" {
  export interface AxiosRequestConfig {
    // Off for auth endpoints, where a 401 is a real credential failure, not an
    // expired token to refresh.
    retryAuth?: boolean;
    // Set once we've already retried a request after a refresh, so we don't loop.
    _retried?: boolean;
  }
}

const api = axios.create({ baseURL: API_URL, withCredentials: true });

/** Read a non-httpOnly cookie (the CSRF token) by name. */
function readCookie(name: string): string | null {
  const m = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return m ? decodeURIComponent(m[1]) : null;
}

// Attach the access token (and CSRF token for cookie-authed routes) to every request.
api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  const csrf = readCookie("csrf_token");
  if (csrf) config.headers["X-CSRF-Token"] = csrf;
  return config;
});

// On a 401, silently refresh the access token and retry the request once. Any
// other error is normalised to a plain Error carrying the backend's message.
api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError<{ error?: { message?: string } }>) => {
    const config = error.config;
    const canRetry = config && config.retryAuth !== false && !config._retried;
    if (error.response?.status === 401 && canRetry) {
      config._retried = true;
      if (await refreshAccessToken()) return api(config);
    }
    const message = error.response?.data?.error?.message ?? error.message;
    return Promise.reject(new Error(message));
  },
);

let refreshInFlight: Promise<boolean> | null = null;

/** Trade the refresh cookie for a fresh access token. Returns success.
 *
 * Single-flight: concurrent callers share one in-flight refresh. Each refresh
 * rotates the token, so firing several at once would make the later ones look
 * like a replay and trip server-side reuse detection, killing the session.
 *
 * Uses bare axios (not the `api` instance) so it never re-enters the 401 interceptor.
 */
export function refreshAccessToken(): Promise<boolean> {
  refreshInFlight ??= doRefresh().finally(() => {
    refreshInFlight = null;
  });
  return refreshInFlight;
}

async function doRefresh(): Promise<boolean> {
  const csrf = readCookie("csrf_token");
  try {
    const { data } = await axios.post<TokenResponse>(`${API_URL}/auth/refresh`, null, {
      withCredentials: true,
      headers: csrf ? { "X-CSRF-Token": csrf } : {},
    });
    setToken(data.access_token);
    return true;
  } catch {
    clearToken();
    return false;
  }
}

// Service functions return the full AxiosResponse — the caller's helper decides
// what to pull out of it (data, a nested field, status, headers). Keeping them as
// thin transport means a change to the response shape only touches the helper.

// --- Auth ---
export function register(email: string, password: string): Promise<AxiosResponse<User>> {
  return api.request<User>({
    method: "POST",
    url: "/auth/register",
    data: { email, password },
    retryAuth: false,
  });
}

export function login(email: string, password: string): Promise<AxiosResponse<TokenResponse>> {
  return api.request<TokenResponse>({
    method: "POST",
    url: "/auth/login",
    data: { email, password },
    retryAuth: false,
  });
}

export function logout(): Promise<AxiosResponse> {
  return api.request({
    method: "POST",
    url: "/auth/logout",
    retryAuth: false,
  });
}

export function getMe(): Promise<AxiosResponse<User>> {
  return api.request<User>({
    method: "GET",
    url: "/auth/me",
  });
}

// --- Sessions ---
export function listSessions(after?: string | null): Promise<AxiosResponse<Page<Session>>> {
  return api.request<Page<Session>>({
    method: "GET",
    url: "/sessions",
    params: { limit: SESSION_PAGE_SIZE, ...(after ? { after } : {}) },
  });
}

export function createSession(title: string | null): Promise<AxiosResponse<Session>> {
  return api.request<Session>({
    method: "POST",
    url: "/sessions",
    data: { title },
  });
}

export function deleteSession(id: string): Promise<AxiosResponse> {
  return api.request({
    method: "DELETE",
    url: `/sessions/${id}`,
  });
}

// One page of a session's messages, newest first. Pass the previous page's
// `next_cursor` as `before` to load older messages.
export function getMessages(
  id: string,
  before?: string | null,
): Promise<AxiosResponse<Page<Message>>> {
  return api.request<Page<Message>>({
    method: "GET",
    url: `/sessions/${id}/messages`,
    params: { limit: MESSAGE_PAGE_SIZE, ...(before ? { before } : {}) },
  });
}

// --- Chat (SSE streaming) ---
// Kept on native fetch: axios buffers the whole response body, so it can't
// deliver tokens one-by-one as they stream in.
function streamFetch(
  sessionId: string,
  content: string,
  signal?: AbortSignal,
): Promise<Response> {
  const token = getToken();
  return fetch(`${API_URL}/chat/${sessionId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
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
export function stopChat(
  sessionId: string,
  generationId: string,
): Promise<AxiosResponse<{ stopped: boolean }>> {
  return api.request<{ stopped: boolean }>({
    method: "POST",
    url: `/chat/${sessionId}/stop/${generationId}`,
  });
}

// --- Usage & billing (Phase 10/11) ---

// Plan quota, month-to-date balance, and recent daily usage for the signed-in user.
export function getUsage(limit = 30): Promise<AxiosResponse<UsageResponse>> {
  return api.request<UsageResponse>({
    method: "GET",
    url: "/usage",
    params: { limit },
  });
}

// The public plan catalog (unauthenticated on the backend, but harmless to send auth).
export function getPlans(): Promise<AxiosResponse<PlansResponse>> {
  return api.request<PlansResponse>({
    method: "GET",
    url: "/plans",
  });
}

// Start a Stripe Checkout for a paid plan; returns the redirect URL.
export function createCheckout(plan: string): Promise<AxiosResponse<CheckoutResponse>> {
  return api.request<CheckoutResponse>({
    method: "POST",
    url: "/billing/checkout",
    data: { plan },
  });
}

// Export a session's full transcript (gated by the plan's `export` feature; 403 otherwise).
export function exportSession(id: string): Promise<AxiosResponse<ExportResponse>> {
  return api.request<ExportResponse>({
    method: "GET",
    url: `/sessions/${id}/export`,
  });
}
