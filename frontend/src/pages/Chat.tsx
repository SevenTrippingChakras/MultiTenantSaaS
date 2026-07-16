import { useEffect, useRef, useState } from "react";
import Sidebar from "../components/Sidebar";
import ChatWindow from "../components/ChatWindow";
import UsagePanel from "../components/UsagePanel";
import { streamChat } from "../api";
import {
  createSession,
  deleteSession,
  downloadSessionExport,
  loadInitialSessions,
  loadLatestMessages,
  loadMoreSessions,
  loadOlderMessages,
  stopChat,
} from "./Chat.helper";
import type { Message, Session } from "../types";

interface ChatProps {
  onLogout: () => void;
}

export default function Chat({ onLogout }: ChatProps) {
  const [sessions, setSessions] = useState<Session[]>([]);
  // Cursor to the next older page of sessions (null when none remain).
  const [sessionsCursor, setSessionsCursor] = useState<string | null>(null);
  const [loadingMoreSessions, setLoadingMoreSessions] = useState(false);
  const [moreSessionsError, setMoreSessionsError] = useState<string | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  // Which view fills the main pane: the chat, or the usage & billing panel.
  const [view, setView] = useState<"chat" | "usage">("chat");
  const [messages, setMessages] = useState<Message[]>([]);
  // Cursor to the next older page of history (null when none remain).
  const [cursor, setCursor] = useState<string | null>(null);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const [olderError, setOlderError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // A transient toast (export result, feature-gate 403, etc.).
  const [notice, setNotice] = useState<string | null>(null);
  // The in-flight stream: its abort controller + the session/generation id we
  // need to cancel it server-side. Refs so the Stop handler always sees the live
  // values, not a stale render's closure.
  const abortRef = useRef<AbortController | null>(null);
  const streamRef = useRef<{ sid: string; genId: string | null } | null>(null);

  useEffect(() => {
    refreshSessions();
  }, []);

  // Auto-dismiss the toast a few seconds after it appears.
  useEffect(() => {
    if (!notice) return;
    const t = setTimeout(() => setNotice(null), 4000);
    return () => clearTimeout(t);
  }, [notice]);

  // Export a session's transcript to a JSON file. A plan without the export
  // feature returns 403, whose message we surface in the toast.
  async function exportSession(id: string) {
    const title = sessions.find((s) => s.id === id)?.title ?? "session";
    try {
      await downloadSessionExport(id, title);
      setNotice("Transcript downloaded.");
    } catch (e) {
      setNotice(e instanceof Error ? e.message : "Export failed");
    }
  }

  async function refreshSessions() {
    const { sessions, cursor } = await loadInitialSessions();
    setSessions(sessions);
    setSessionsCursor(cursor);
  }

  // Append the next older page of sessions when the user asks for more.
  async function loadMore() {
    if (!sessionsCursor || loadingMoreSessions) return;
    setLoadingMoreSessions(true);
    setMoreSessionsError(null);
    try {
      const more = await loadMoreSessions(sessionsCursor);
      setSessions((s) => [...s, ...more.sessions]);
      setSessionsCursor(more.cursor);
    } catch (e) {
      setMoreSessionsError(e instanceof Error ? e.message : "Failed to load more");
    } finally {
      setLoadingMoreSessions(false);
    }
  }

  async function selectSession(id: string) {
    setView("chat");
    setActiveId(id);
    setOlderError(null);
    const { messages, cursor } = await loadLatestMessages(id);
    setMessages(messages);
    setCursor(cursor);
  }

  // Prepend the next older page when the user scrolls back through history.
  async function loadOlder() {
    if (!activeId || !cursor || loadingOlder) return;
    setLoadingOlder(true);
    setOlderError(null);
    try {
      const older = await loadOlderMessages(activeId, cursor);
      setMessages((m) => [...older.messages, ...m]);
      setCursor(older.cursor);
    } catch (e) {
      setOlderError(e instanceof Error ? e.message : "Failed to load older messages");
    } finally {
      setLoadingOlder(false);
    }
  }

  // New chat clears the view; the session is created on the first message
  // (so we never leave empty sessions lying around), mirroring ChatGPT.
  function newChat() {
    setView("chat");
    setActiveId(null);
    setMessages([]);
    setCursor(null);
    setOlderError(null);
  }

  async function removeSession(id: string) {
    await deleteSession(id);
    if (id === activeId) {
      setActiveId(null);
      setMessages([]);
      setCursor(null);
    }
    await refreshSessions();
  }

  // Stop the current stream: abort the fetch (instant UI) and tell the server to
  // cancel it (works even if a proxy buffers the connection). Best-effort.
  async function stop() {
    const info = streamRef.current;
    abortRef.current?.abort();
    if (info?.genId) {
      try {
        await stopChat(info.sid, info.genId);
      } catch {
        /* already finished, or nothing listening */
      }
    }
  }

  async function send(text: string) {
    setBusy(true);
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      let sid = activeId;
      if (!sid) {
        const s = await createSession(null);
        sid = s.id;
        setActiveId(sid);
      }
      streamRef.current = { sid, genId: null };

      // Optimistically show the user message and an empty assistant bubble.
      setMessages((m) => [
        ...m,
        { role: "user", content: text },
        { role: "assistant", content: "" },
      ]);

      await streamChat(
        sid,
        text,
        (delta) => {
          setMessages((m) => {
            const copy = [...m];
            const last = copy[copy.length - 1];
            copy[copy.length - 1] = { ...last, content: last.content + delta };
            return copy;
          });
        },
        {
          signal: controller.signal,
          onGenerationId: (id) => {
            if (streamRef.current) streamRef.current.genId = id;
          },
        },
      );

      await refreshSessions(); // reflect new title / updated order
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Something went wrong";
      // Put the error into the pending assistant bubble instead of leaving it blank.
      setMessages((m) => {
        const copy = [...m];
        const last = copy[copy.length - 1];
        if (last && last.role === "assistant") {
          copy[copy.length - 1] = {
            ...last,
            content: last.content ? `${last.content}\n\n⚠️ ${msg}` : `⚠️ ${msg}`,
          };
        }
        return copy;
      });
    } finally {
      setBusy(false);
      abortRef.current = null;
      streamRef.current = null;
    }
  }

  return (
    <div className="flex h-screen gap-3 p-3">
      <Sidebar
        sessions={sessions}
        activeId={activeId}
        onSelect={selectSession}
        onNew={newChat}
        onDelete={removeSession}
        onExport={exportSession}
        onUsage={() => setView("usage")}
        onLogout={onLogout}
        hasMore={sessionsCursor !== null}
        loadingMore={loadingMoreSessions}
        moreError={moreSessionsError}
        onLoadMore={loadMore}
      />
      {view === "usage" ? (
        <UsagePanel onClose={() => setView("chat")} />
      ) : (
        <ChatWindow
          messages={messages}
          onSend={send}
          onStop={stop}
          busy={busy}
          hasOlder={cursor !== null}
          loadingOlder={loadingOlder}
          olderError={olderError}
          onLoadOlder={loadOlder}
        />
      )}
      {notice && (
        <div className="glass fixed bottom-6 left-1/2 z-50 -translate-x-1/2 rounded-xl border border-white/15 px-4 py-2.5 text-sm shadow-xl">
          {notice}
        </div>
      )}
    </div>
  );
}
