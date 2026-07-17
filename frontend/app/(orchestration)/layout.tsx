/**
 * Orchestration layout - provides navigation sidebar for orchestration sub-pages.
 */

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ProtectedRoute } from "@/components/auth/protected-route";

const NAV_ITEMS = [
  { href: "/orchestration", label: "Dashboard", exact: true },
  { href: "/orchestration/execute", label: "Execute" },
  { href: "/orchestration/agents", label: "Agents" },
  { href: "/orchestration/history", label: "History" },
];

function OrchestrationNav() {
  const pathname = usePathname();

  return (
    <aside className="w-56 border-r border-gray-800 bg-gray-900/50 shrink-0">
      <div className="px-4 py-5 border-b border-gray-800">
        <h2 className="text-sm font-semibold text-gray-200 uppercase tracking-wider">
          Orchestration
        </h2>
        <p className="text-[10px] text-gray-500 mt-1">AI Engine Control</p>
      </div>
      <nav className="p-2 space-y-0.5">
        {NAV_ITEMS.map((item) => {
          const isActive = item.exact
            ? pathname === item.href
            : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`block px-3 py-2 rounded-md text-sm transition-colors ${
                isActive
                  ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
                  : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 border border-transparent"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

export default function OrchestrationLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ProtectedRoute>
      <div className="min-h-screen flex bg-gray-950">
        <OrchestrationNav />
        <div className="flex-1 flex flex-col min-w-0">
          <header className="h-12 border-b border-gray-800 flex items-center justify-between px-6 shrink-0">
            <h1 className="text-sm font-semibold text-gray-200">
              StadiumMind OS — Orchestration Engine
            </h1>
            <span className="text-[10px] text-gray-500 font-mono bg-gray-800 px-2 py-0.5 rounded">
              v1.0.0
            </span>
          </header>
          <main className="flex-1 overflow-auto p-6">{children}</main>
        </div>
      </div>
    </ProtectedRoute>
  );
}
