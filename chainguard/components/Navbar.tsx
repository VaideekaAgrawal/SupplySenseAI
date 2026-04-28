"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";
import { api } from "@/lib/api";

export default function Navbar() {
  const pathname = usePathname();
  const [resilience, setResilience] = useState<number | null>(null);
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    api.resilience().then((r) => setResilience(r.score)).catch(() => {});
    api.alerts(true).then((r) => setUnread(r.unread)).catch(() => {});
    const iv = setInterval(() => {
      api.resilience().then((r) => setResilience(r.score)).catch(() => {});
    }, 30000);
    return () => clearInterval(iv);
  }, []);

  const resColor =
    resilience === null ? "text-slate-400"
    : resilience >= 80 ? "text-green-400"
    : resilience >= 60 ? "text-amber-400"
    : "text-red-400";

  const navLink = (href: string, label: string) => (
    <Link
      key={href}
      href={href}
      className={`text-sm font-medium px-3 py-1.5 rounded-md transition-colors ${
        pathname.startsWith(href)
          ? "bg-blue-600/30 text-blue-300"
          : "text-slate-400 hover:text-white hover:bg-slate-700/50"
      }`}
    >
      {label}
    </Link>
  );

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-navy-900/95 backdrop-blur border-b border-slate-800 h-16 flex items-center px-6">
      {/* Brand */}
      <Link href="/dashboard" className="flex items-center gap-2 mr-8">
        <span className="text-xl">⛓️</span>
        <span className="font-bold text-white text-lg tracking-tight">SupplySense</span>
        <span className="text-blue-400 font-light text-sm">AI</span>
      </Link>

      {/* Nav links */}
      <div className="flex items-center gap-1 flex-1">
        {navLink("/dashboard", "Dashboard")}
        {navLink("/create", "Create")}
        {navLink("/nodes", "Nodes")}
        {navLink("/simulate", "Simulate")}
        {navLink("/cascade", "Cascade")}
        {navLink("/reroute", "Reroute")}
        {navLink("/chat", "AI Chat")}
      </div>

      {/* Right side — resilience score + alerts */}
      <div className="flex items-center gap-4">
        {/* Live indicator */}
        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          <span className="w-1.5 h-1.5 rounded-full bg-green-400 pulse-dot" />
          LIVE
        </div>

        {/* Resilience badge */}
        <div className="flex items-center gap-2 bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-1.5">
          <span className="text-xs text-slate-400">Resilience</span>
          <span className={`font-bold text-sm ${resColor}`}>
            {resilience !== null ? `${resilience.toFixed(0)}/100` : "—"}
          </span>
        </div>

        {/* Alerts */}
        <Link href="/dashboard" className="relative text-slate-400 hover:text-white">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
          </svg>
          {unread > 0 && (
            <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white text-[10px] rounded-full flex items-center justify-center font-bold">
              {unread > 9 ? "9+" : unread}
            </span>
          )}
        </Link>
      </div>
    </nav>
  );
}
