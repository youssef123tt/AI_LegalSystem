import React from "react";
import { NavLink } from "react-router-dom";
import clsx from "clsx";
import { FileUp, Search, Layers, Activity, BookOpenText, Map, MessageCircle, FileText } from "lucide-react";

const nav = [
  { to: "/", label: "Upload", icon: FileUp },
  { to: "/jobs", label: "Jobs", icon: Activity },
  { to: "/search", label: "Search", icon: Search },
  { to: "/chat", label: "RAG Chat", icon: MessageCircle },
  { to: "/report", label: "Reports", icon: FileText },
  { to: "/outline", label: "Outline", icon: Map },
  { to: "/chunks", label: "Chunks", icon: Layers },
  { to: "/about", label: "About", icon: BookOpenText }
];

export function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <div className="mx-auto max-w-6xl px-4 py-6">
        <header className="mb-6 flex items-end justify-between gap-4">
          <div>
            <div className="font-display text-2xl font-black tracking-tight text-ink-900">
              AI Legal Knowledge Assistant
            </div>
            <div className="text-sm text-ink-700">
              Upload documents, track ingestion, search chunks (Milestone 3).
            </div>
          </div>
          <div className="text-right text-xs text-ink-600">
            API proxied via Vite to <span className="font-mono">localhost:8000</span>
          </div>
        </header>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-[240px_1fr]">
          <aside className="rounded-xl bg-white/55 p-2 shadow-card ring-1 ring-black/5 backdrop-blur">
            <nav className="flex flex-col gap-1">
              {nav.map((n) => (
                <NavLink
                  key={n.to}
                  to={n.to}
                  className={({ isActive }) =>
                    clsx(
                      "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold",
                      isActive
                        ? "bg-ink-900 text-paper"
                        : "text-ink-900 hover:bg-black/5 active:bg-black/10"
                    )
                  }
                >
                  <n.icon size={16} />
                  {n.label}
                </NavLink>
              ))}
            </nav>
            <div className="mt-4 rounded-lg bg-paper p-3 text-xs text-ink-700 ring-1 ring-black/5">
              Tip: After upload, wait for job <span className="font-mono">status=complete</span> before expecting
              chunks/search hits.
            </div>
          </aside>

          <main>{children}</main>
        </div>
      </div>
    </div>
  );
}
