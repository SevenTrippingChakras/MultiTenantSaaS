import { useEffect, useState } from "react";
import Sidebar from "../components/Sidebar";
import ChatWindow from "../components/ChatWindow";
import {
  createSession,
  deleteSession,
  getMessages,
  listSessions,
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

  async function send(text: string) {
    setBusy(true);
    try {
      let sid = activeId;
      if (!sid) {
        const s = await createSession(null);
        sid = s.id;
        setActiveId(sid);
      }

      // Optimistically show the user message and an empty assistant bubble.
      setMessages((m) => [
        ...m,
        { role: "user", content: text },
        { role: "assistant", content: "" },
      ]);

      await streamChat(sid, text, (delta) => {
        setMessages((m) => {
          const copy = [...m];
          const last = copy[copy.length - 1];
          copy[copy.length - 1] = { ...last, content: last.content + delta };
          return copy;
        });
      });

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
      <ChatWindow messages={messages} onSend={send} busy={busy} />
    </div>
  );
}
