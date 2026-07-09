import { useState } from "react";
import {
  Flame,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Trash2,
} from "lucide-react";
import type { Session } from "../types";
import { cn } from "@/lib/utils";

interface SidebarProps {
  sessions: Session[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onLogout: () => void;
}

export default function Sidebar({
  sessions,
  activeId,
  onSelect,
  onNew,
  onDelete,
  onLogout,
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={cn(
        "glass flex flex-col gap-3 rounded-2xl p-3 transition-[width] duration-300",
        collapsed ? "w-16" : "w-72",
      )}
    >
      <div className="flex items-center justify-between border-b border-white/10 px-1 pb-3">
        {!collapsed && (
          <div className="flex items-center gap-2">
            <Flame className="size-5 text-ember" />
            <span className="text-lg font-bold tracking-tight">AIchat</span>
          </div>
        )}
        <button
          onClick={() => setCollapsed((c) => !c)}
          title={collapsed ? "Expand" : "Collapse"}
          className={cn(
            "text-muted-foreground transition hover:text-moss",
            collapsed && "mx-auto",
          )}
        >
          {collapsed ? (
            <PanelLeftOpen className="size-5" />
          ) : (
            <PanelLeftClose className="size-5" />
          )}
        </button>
      </div>

      <button
        onClick={onNew}
        title="New chat"
        className="flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-ember to-[#ff6f2a] py-2.5 font-semibold text-[#2a1400] shadow-lg shadow-ember/25 transition hover:brightness-105 active:scale-[0.98]"
      >
        <Plus className="size-5 stroke-[3]" />
        {!collapsed && "New chat"}
      </button>

      {!collapsed && (
        <>
          <p className="px-2 pt-1 text-xs font-semibold tracking-widest text-muted-foreground uppercase">
            Sessions
          </p>
          <div className="flex-1 overflow-y-auto">
            <div className="flex flex-col gap-1 pr-1">
              {sessions.map((s) => {
                const active = s.id === activeId;
                return (
                  <div
                    key={s.id}
                    onClick={() => onSelect(s.id)}
                    className={cn(
                      "group flex cursor-pointer items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition",
                      active
                        ? "bg-moss/15 text-foreground ring-1 ring-moss/40"
                        : "text-muted-foreground hover:bg-white/5 hover:text-foreground",
                    )}
                  >
                    <span
                      className={cn(
                        "size-1.5 shrink-0 rounded-full",
                        active ? "pulse-dot bg-moss" : "bg-transparent",
                      )}
                    />
                    <span className="flex-1 truncate">{s.title}</span>
                    <button
                      title="Delete"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDelete(s.id);
                      }}
                      className="shrink-0 text-muted-foreground opacity-0 transition hover:text-destructive group-hover:opacity-100"
                    >
                      <Trash2 className="size-4" />
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}
      {collapsed && <div className="flex-1" />}

      <button
        onClick={onLogout}
        title="Log out"
        className="flex items-center justify-center gap-2 rounded-lg border border-transparent py-2 text-sm font-medium text-muted-foreground transition hover:border-white/10 hover:text-foreground"
      >
        <LogOut className="size-4" />
        {!collapsed && "Log out"}
      </button>
    </aside>
  );
}
