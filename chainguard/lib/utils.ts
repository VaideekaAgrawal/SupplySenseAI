/**
 * Utility helpers for formatting INR, risk levels, etc.
 */

export function formatINR(amount: number): string {
  if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`;
  if (amount >= 1000) return `₹${(amount / 1000).toFixed(1)}K`;
  return `₹${Math.round(amount)}`;
}

export function riskColor(level: string): string {
  switch (level?.toUpperCase()) {
    case "CRITICAL": return "text-red-400";
    case "HIGH": return "text-amber-400";
    case "MEDIUM": return "text-yellow-300";
    case "LOW": return "text-green-400";
    default: return "text-slate-400";
  }
}

export function riskBg(level: string): string {
  switch (level?.toUpperCase()) {
    case "CRITICAL": return "bg-red-900/40 border-red-700";
    case "HIGH": return "bg-amber-900/40 border-amber-700";
    case "MEDIUM": return "bg-yellow-900/30 border-yellow-700";
    case "LOW": return "bg-green-900/30 border-green-700";
    default: return "bg-slate-800 border-slate-700";
  }
}

export function riskBadge(level: string): string {
  switch (level?.toUpperCase()) {
    case "CRITICAL": return "bg-red-500/20 text-red-300 border border-red-500/40";
    case "HIGH": return "bg-amber-500/20 text-amber-300 border border-amber-500/40";
    case "MEDIUM": return "bg-yellow-500/20 text-yellow-300 border border-yellow-500/40";
    case "LOW": return "bg-green-500/20 text-green-300 border border-green-500/40";
    default: return "bg-slate-700 text-slate-300";
  }
}

export function severityColor(severity: number): string {
  if (severity >= 0.75) return "text-red-400";
  if (severity >= 0.5) return "text-amber-400";
  return "text-yellow-300";
}

export function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function cn(...classes: (string | undefined | false | null)[]): string {
  return classes.filter(Boolean).join(" ");
}
