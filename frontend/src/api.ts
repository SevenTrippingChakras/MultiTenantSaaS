import { API_URL } from "./config";
import { getToken } from "./token";
import type { Message, Session, TokenResponse, User } from "./types";

interface RequestOptions {
  method?: string;
  body?: unknown;
}

// Core request helper: attaches the JWT and parses JSON.
async function request<T>(
  path: string,
  { method = "GET", body }: RequestOptions = {},
): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed: ${res.status}`);
  }
  return res.status === 204 ? (null as T) : res.json();
}

// --- Auth ---
export const register = (email: string, password: string) =>
  request<User>("/auth/register", { method: "POST", body: { email, password } });

export const login = (email: string, password: string) =>
  request<TokenResponse>("/auth/login", {
    method: "POST",
    body: { email, password },
  });

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
// Calls onToken(delta) for each token; resolves when the stream ends.
export async function streamChat(
  sessionId: string,
  content: string,
  onToken: (delta: string) => void,
): Promise<void> {
  const res = await fetch(`${API_URL}/chat/${sessionId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${getToken()}`,
    },
    body: JSON.stringify({ content }),
  });
  if (!res.ok || !res.body) throw new Error(`Chat failed: ${res.status}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by a blank line.
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      const line = frame.trim();
      if (!line.startsWith("data:")) continue;
      const obj = JSON.parse(line.slice(5).trim());
      if (obj.error) throw new Error(obj.error);
      if (obj.done) return;
      if (obj.delta) onToken(obj.delta);
    }
  }
}
