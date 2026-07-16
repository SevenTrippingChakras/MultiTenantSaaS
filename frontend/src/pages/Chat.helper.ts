import {
  createSession as createSessionApi,
  deleteSession as deleteSessionApi,
  exportSession as exportSessionApi,
  getMessages,
  listSessions,
  stopChat as stopChatApi,
} from "../api";
import type { Message, Session } from "../types";

// Helpers for the Chat page: they call the service functions (which return the
// full response) and pull out exactly what the page needs, so the components
// stay free of response-shape details.

// --- Sessions ---
export interface LoadedSessions {
  sessions: Session[];
  cursor: string | null;
}

export async function loadInitialSessions(): Promise<LoadedSessions> {
  const response = await listSessions();
  return { sessions: response.data.items, cursor: response.data.next_cursor };
}

export async function loadMoreSessions(after: string): Promise<LoadedSessions> {
  const response = await listSessions(after);
  return { sessions: response.data.items, cursor: response.data.next_cursor };
}

export async function createSession(title: string | null): Promise<Session> {
  const response = await createSessionApi(title);
  return response.data;
}

export async function deleteSession(id: string): Promise<void> {
  await deleteSessionApi(id);
}

// --- Messages ---
export interface LoadedMessages {
  messages: Message[];
  cursor: string | null;
}

export async function loadLatestMessages(sessionId: string): Promise<LoadedMessages> {
  const response = await getMessages(sessionId);
  return { messages: response.data.items, cursor: response.data.next_cursor };
}

export async function loadOlderMessages(
  sessionId: string,
  before: string,
): Promise<LoadedMessages> {
  const response = await getMessages(sessionId, before);
  return { messages: response.data.items, cursor: response.data.next_cursor };
}

// --- Chat control ---
export async function stopChat(sessionId: string, generationId: string): Promise<void> {
  await stopChatApi(sessionId, generationId);
}

// --- Export (feature-gated) ---

function fileSlug(title: string): string {
  return (
    title
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 40) || "session"
  );
}

// Fetch a session's transcript and save it as a JSON file. Throws (propagating
// the backend's message, e.g. a 403 on a plan without the export feature) so the
// caller can surface it.
export async function downloadSessionExport(id: string, title: string): Promise<void> {
  const { data } = await exportSessionApi(id);
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${fileSlug(title)}.json`;
  a.click();
  URL.revokeObjectURL(url);
}
