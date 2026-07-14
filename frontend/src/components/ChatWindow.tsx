import { useEffect, useRef, useState, type FormEvent } from "react";
import { Flame, Send, Square } from "lucide-react";
import type { Message } from "../types";
import { cn } from "@/lib/utils";

interface ChatWindowProps {
  messages: Message[];
  onSend: (text: string) => void;
  onStop: () => void;
  busy: boolean;
  hasOlder: boolean;
  loadingOlder: boolean;
  olderError: string | null;
  onLoadOlder: () => void;
}

export default function ChatWindow({
  messages,
  onSend,
  onStop,
  busy,
  hasOlder,
  loadingOlder,
  olderError,
  onLoadOlder,
}: ChatWindowProps) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  // Scroll to the newest message when one is sent or streamed. Keyed on the last
  // message so prepending older history (which leaves the last one unchanged)
  // doesn't yank the view back to the bottom.
  const last = messages[messages.length - 1];
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [last?.role, last?.content]);

  function submit(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    onSend(text);
  }

  return (
    <main className="glass flex flex-1 flex-col overflow-hidden rounded-2xl">
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto flex max-w-3xl flex-col gap-6 px-5 py-8">
          {hasOlder && (
            <div className="flex flex-col items-center gap-1.5">
              <button
                onClick={onLoadOlder}
                disabled={loadingOlder}
                className="rounded-full border border-white/15 bg-white/5 px-4 py-1.5 text-sm text-muted-foreground transition hover:text-foreground disabled:opacity-50"
              >
                {loadingOlder ? "Loading…" : olderError ? "Retry" : "Load older messages"}
              </button>
              {olderError && <p className="text-xs text-destructive">{olderError}</p>}
            </div>
          )}

          {messages.length === 0 && (
            <div className="mt-28 flex flex-col items-center gap-5 text-center">
              <div className="flex size-20 items-center justify-center rounded-2xl bg-gradient-to-br from-ember to-[#ff6f2a] shadow-xl shadow-ember/30">
                <Flame className="float-y size-10 text-[#2a1400]" />
              </div>
              <div>
                <p className="text-2xl font-bold">Pull up a seat by the fire</p>
                <p className="mt-1 text-muted-foreground">
                  Send a message to start a new conversation.
                </p>
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <div
              key={m.id ?? `pending-${i}`}
              className={cn(
                "animate-pop-in flex items-end gap-2.5",
                m.role === "user" ? "justify-end" : "justify-start",
              )}
            >
              {m.role === "assistant" && (
                <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-moss/20 ring-1 ring-moss/40">
                  <Flame className="size-4 text-moss" />
                </div>
              )}
              <div
                className={cn(
                  "relative max-w-[74%] rounded-2xl px-4 py-2.5 leading-relaxed whitespace-pre-wrap",
                  m.role === "user"
                    ? "bubble-r bg-ember font-medium text-[#2a1400]"
                    : "bubble-l border border-white/15 bg-[#17403a] text-foreground",
                )}
              >
                {m.content ||
                  (busy && i === messages.length - 1 ? (
                    <span className="inline-flex gap-1">
                      <span className="size-2 animate-bounce rounded-full bg-moss [animation-delay:-0.3s]" />
                      <span className="size-2 animate-bounce rounded-full bg-moss [animation-delay:-0.15s]" />
                      <span className="size-2 animate-bounce rounded-full bg-moss" />
                    </span>
                  ) : (
                    <span className="text-muted-foreground italic">stopped</span>
                  ))}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      </div>

      <div className="border-t border-white/10 p-4">
        <form onSubmit={submit} className="mx-auto flex max-w-3xl items-center gap-3">
          <input
            placeholder="Message AIchat…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={busy}
            className="h-12 flex-1 rounded-xl border border-white/15 bg-white/5 px-4 text-base text-foreground placeholder:text-muted-foreground focus:border-moss/60 focus:outline-none focus:ring-2 focus:ring-moss/30"
          />
          {busy ? (
            <button
              type="button"
              onClick={onStop}
              aria-label="Stop generating"
              className="flex size-12 shrink-0 items-center justify-center rounded-xl border border-ember/60 bg-ember/15 text-ember shadow-lg shadow-ember/10 transition hover:bg-ember/25 active:scale-95"
            >
              <Square className="size-5 fill-current" />
            </button>
          ) : (
            <button
              type="submit"
              disabled={!input.trim()}
              aria-label="Send message"
              className={cn(
                "flex size-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-ember to-[#ff6f2a] text-[#2a1400] shadow-lg shadow-ember/25 transition",
                !input.trim() ? "opacity-40" : "hover:brightness-105 active:scale-95",
              )}
            >
              <Send className="size-5 stroke-[2.5]" />
            </button>
          )}
        </form>
      </div>
    </main>
  );
}
