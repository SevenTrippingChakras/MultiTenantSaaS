import { useEffect, useRef, useState } from "react";
import Sidebar from "../components/Sidebar";
import ChatWindow from "../components/ChatWindow";
import {
  createSession,
  deleteSession,
  getMessages,
  listSessions,
  stopChat,
  streamChat,
} from "../api";
import type { Message, Session } from "../types";

interface ChatProps {
  onLogout: () => void;
}

export default function Chat({ onLogout }: ChatProps) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [busy, setBusy] = useState(false);
  // The in-flight stream: its abort controller + the session/generation id we
  // need to cancel it server-side. Refs so the Stop handler always sees the live
  // values, not a stale render's closure.
  const abortRef = useRef<AbortController | null>(null);
  const streamRef = useRef<{ sid: string; genId: string | null } | null>(null);

  useEffect(() => {
    refreshSessions();
  }, []);

  async function refreshSessions() {
    setSessions(await listSessions());
  }

  async function selectSession(id: string) {
    setActiveId(id);
    setMessages(await getMessages(id));
  }

  // New chat clears the view; the session is created on the first message
  // (so we never leave empty sessions lying around), mirroring ChatGPT.
  function newChat() {
    setActiveId(null);
    setMessages([]);
  }

  async function removeSession(id: string) {
    await deleteSession(id);
    if (id === activeId) {
      setActiveId(null);
      setMessages([]);
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
        onLogout={onLogout}
      />
      <ChatWindow messages={messages} onSend={send} onStop={stop} busy={busy} />
    </div>
  );
}
