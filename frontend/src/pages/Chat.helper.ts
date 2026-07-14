import {
  createSession as createSessionApi,
  deleteSession as deleteSessionApi,
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
