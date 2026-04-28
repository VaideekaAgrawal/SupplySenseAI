"use client";
import { useEffect, useState, useRef } from "react";
import {
  api,
  KPIData,
  Shipment,
  Disruption,
  TopRiskShipment,
  RiskExplanation,
} from "@/lib/api";
import { formatINR, riskColor, riskBadge, timeAgo } from "@/lib/utils";
import Link from "next/link";
import { DynamicMap } from "@/components/DynamicMap";
import type { MapMarker, MapRoute } from "@/components/DynamicMap";

// ── KPI Bar ────────────────────────────────────────────────────────────────────

function KpiBar({ kpis }: { kpis: KPIData }) {
  const cards = [
    { label: "Active Shipments", value: kpis.active_shipments, color: "text-blue-400" },
    { label: "At Risk", value: kpis.at_risk_count, color: "text-amber-400" },
    { label: "Disrupted", value: kpis.disrupted_count, color: "text-red-400" },
    { label: "Revenue at Risk", value: formatINR(kpis.revenue_at_risk), color: "text-red-300" },
    {
      label: "Resilience Score",
      value: `${kpis.resilience_score.toFixed(0)}/100`,
      color: kpis.resilience_score >= 70 ? "text-green-400" : "text-amber-400",
    },
    { label: "Revenue Saved Today", value: formatINR(kpis.revenue_saved_today), color: "text-green-400" },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
      {cards.map((c) => (
        <div key={c.label} className="bg-navy-800 border border-slate-700 rounded-xl p-4">
          <div className="text-xs text-slate-400 mb-1">{c.label}</div>
          <div className={`text-2xl font-bold ${c.color}`}>{c.value}</div>
        </div>
      ))}
    </div>
  );
}

// ── Disruption Cards ───────────────────────────────────────────────────────────

function DisruptionCards({ disruptions }: { disruptions: Disruption[] }) {
  if (!disruptions.length) return null;
  return (
    <div className="mb-6">
      <h2 className="text-sm font-semibold text-slate-300 mb-3 uppercase tracking-wider">
        🔴 Active Disruptions (India)
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {disruptions.map((d) => (
          <Link key={d.id} href={`/cascade/${d.id}`} className="block">
            <div className="bg-red-950/30 border border-red-800/60 rounded-xl p-4 hover:border-red-600 transition-colors cursor-pointer glow-red">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <div className="font-semibold text-red-300">{d.title}</div>
                  <div className="text-xs text-slate-400 mt-0.5">
                    {d.location.city}, {d.location.state}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs text-slate-500">{timeAgo(d.detected_at)}</div>
                  <div className="text-sm font-bold text-red-400 mt-1">
                    {Math.round(d.severity * 100)}% severity
                  </div>
                </div>
              </div>
              {d.cascade && (
                <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-red-800/40">
                  <div className="text-center">
                    <div className="text-lg font-bold text-white">{d.cascade.total_shipments}</div>
                    <div className="text-xs text-slate-400">shipments</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-bold text-amber-400">{formatINR(d.cascade.revenue_at_risk)}</div>
                    <div className="text-xs text-slate-400">revenue</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-bold text-red-300">{d.cascade.customers_affected.toLocaleString()}</div>
                    <div className="text-xs text-slate-400">customers</div>
                  </div>
                </div>
              )}
              <div className="mt-3 text-xs text-blue-400 font-medium">→ View cascade tree</div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

// ── Risk Tooltip Component ──────────────────────────────────────────────────

function RiskTooltip({ explanation, visible }: { explanation: RiskExplanation | null; visible: boolean }) {
  if (!visible || !explanation) return null;
  return (
    <div className="absolute z-50 left-0 top-full mt-2 w-80 bg-navy-900 border border-slate-600 rounded-xl p-4 shadow-2xl text-left">
      <div className="text-xs text-slate-400 mb-2 font-medium">WHY THIS RISK SCORE?</div>
      <p className="text-sm text-slate-300 mb-3">{explanation.summary}</p>
      <div className="space-y-2">
        {explanation.factors.map((f, i) => (
          <div key={i} className="flex items-start gap-2">
            <span className="text-base">{f.icon}</span>
            <div className="flex-1">
              <div className="flex justify-between">
                <span className="text-xs font-semibold text-slate-200">{f.name}</span>
                <span className="text-xs text-blue-400 font-bold">{f.contribution_pct}%</span>
              </div>
              <div className="text-xs text-slate-400">{f.detail}</div>
            </div>
          </div>
        ))}
      </div>
      <div className="mt-3 pt-2 border-t border-slate-700 grid grid-cols-3 gap-2 text-xs">
        <div><span className="text-slate-500">Route:</span> <span className="text-slate-300">{explanation.route}</span></div>
        <div><span className="text-slate-500">Carrier:</span> <span className="text-slate-300">{explanation.carrier}</span></div>
        <div><span className="text-slate-500">Confidence:</span> <span className="text-slate-300">{(explanation.confidence * 100).toFixed(0)}%</span></div>
      </div>
    </div>
  );
}

// ── Top 5 High-Risk Panel with Auto-Reroutes + Route Graph ─────────────────

function TopRiskPanel({ topRisk }: { topRisk: TopRiskShipment[] }) {
  if (!topRisk.length) return null;

  const markers: MapMarker[] = [];
  const routes: MapRoute[] = [];
  const addedCities = new Set<string>();

  topRisk.forEach((tr, idx) => {
    const s = tr.shipment;
    const riskColors = ["red", "red", "amber", "amber", "amber"];
    const color = riskColors[idx] || "amber";

    if (!addedCities.has(s.origin.city)) {
      markers.push({ lat: s.origin.lat, lng: s.origin.lng, label: s.origin.city, color: "blue", radius: 7, popup: `<b>${s.origin.city}</b><br/>Origin for ${s.id}` });
      addedCities.add(s.origin.city);
    }
    if (!addedCities.has(s.destination.city)) {
      markers.push({ lat: s.destination.lat, lng: s.destination.lng, label: s.destination.city, color: "cyan", radius: 7, popup: `<b>${s.destination.city}</b><br/>Dest for ${s.id}` });
      addedCities.add(s.destination.city);
    }

    routes.push({ waypoints: s.route.waypoints, color, weight: 3, dashArray: "8 4", label: `${s.id} (original)` });

    if (tr.reroute?.recommended?.waypoints?.length) {
      routes.push({ waypoints: tr.reroute.recommended.waypoints, color: "green", weight: 3, label: `${s.id} → ${tr.reroute.recommended.name}` });
    }
  });

  return (
    <div className="mb-6">
      <h2 className="text-sm font-semibold text-slate-300 mb-3 uppercase tracking-wider">
        🚨 Top 5 High-Risk Shipments — Auto-Reroute Suggestions
      </h2>

      <div className="mb-4 rounded-xl overflow-hidden border border-slate-700">
        <DynamicMap markers={markers} routes={routes} height="380px" zoom={5} />
        <div className="bg-navy-800 px-4 py-2 flex flex-wrap gap-4 text-xs text-slate-400 border-t border-slate-700">
          <span className="flex items-center gap-1"><span className="w-4 h-0.5 inline-block" style={{ borderBottom: "2px dashed #f87171" }}></span> Original (disrupted)</span>
          <span className="flex items-center gap-1"><span className="w-4 h-0.5 bg-green-400 inline-block"></span> Recommended reroute</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-400 inline-block"></span> Origin</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-cyan-400 inline-block"></span> Destination</span>
        </div>
      </div>

      <div className="space-y-3">
        {topRisk.map((tr) => {
          const s = tr.shipment;
          const rec = tr.reroute?.recommended;
          const comp = tr.reroute?.comparison;
          return (
            <div key={s.id} className="bg-navy-800 border border-slate-700 rounded-xl p-4">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-blue-400 font-bold text-lg">{s.id}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${riskBadge(s.risk_level)}`}>{s.risk_level}</span>
                  <span className="text-slate-400 text-sm">{s.origin.city} → {s.destination.city}</span>
                  <span className="text-slate-500 text-xs">· {s.carrier} · {s.shipping_mode}</span>
                </div>
                <div className="text-right">
                  <span className={`text-2xl font-bold ${riskColor(s.risk_level)}`}>{s.risk_score.toFixed(0)}</span>
                  <span className="text-slate-500 text-sm">/100</span>
                </div>
              </div>

              <div className="bg-slate-800/50 rounded-lg p-3 mb-3">
                <div className="text-xs text-slate-400 mb-2 font-semibold uppercase">Risk Breakdown</div>
                <p className="text-sm text-slate-300 mb-2">{tr.risk_explanation.summary}</p>
                <div className="flex flex-wrap gap-3">
                  {tr.risk_explanation.factors.map((f, i) => (
                    <div key={i} className="flex items-center gap-1.5 text-xs">
                      <span>{f.icon}</span>
                      <span className="text-slate-300">{f.name}</span>
                      <span className="text-blue-400 font-bold">{f.contribution_pct}%</span>
                    </div>
                  ))}
                </div>
              </div>

              {rec && (
                <div className="bg-green-950/20 border border-green-800/40 rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-green-400 font-semibold text-sm">✅ Recommended Reroute:</span>
                    <span className="text-white text-sm font-medium">{rec.name}</span>
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-2">
                    {[
                      { v: `${rec.time_hours.toFixed(1)}h`, l: "Time", c: "text-cyan-400" },
                      { v: formatINR(rec.cost_inr), l: "Cost", c: "text-blue-300" },
                      { v: `${rec.risk_score.toFixed(0)}%`, l: "New Risk", c: "text-green-400" },
                      { v: `${rec.carbon_kg.toFixed(0)} kg`, l: "Carbon", c: "text-green-300" },
                    ].map((m) => (
                      <div key={m.l} className="text-center">
                        <div className={`font-bold ${m.c}`}>{m.v}</div>
                        <div className="text-xs text-slate-500">{m.l}</div>
                      </div>
                    ))}
                  </div>
                  {rec.recommendation_reason && (
                    <p className="text-xs text-green-300/80 bg-green-950/30 border border-green-800/30 rounded px-2 py-1 mb-2">
                      💡 {rec.recommendation_reason}
                    </p>
                  )}
                  {comp && (
                    <div className="flex gap-4 text-xs">
                      <span className="text-red-400">
                        Do nothing: {String((comp.do_nothing as Record<string, unknown>).risk_score)}% risk, -{formatINR(Number((comp.do_nothing as Record<string, unknown>).revenue_lost_inr || 0))} revenue
                      </span>
                      <span className="text-green-400">
                        Reroute: +{formatINR(Number((comp.recommended as Record<string, unknown>).revenue_saved_inr || 0))} saved
                      </span>
                    </div>
                  )}
                  <div className="mt-2">
                    <Link href={`/reroute/${s.id}`} className="text-xs text-blue-400 hover:text-blue-300 font-medium underline">
                      View all routes & accept →
                    </Link>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Shipment Table with Risk Hover Tooltip, Filters, Pagination, Delete ─────

const STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "on_track", label: "On Track" },
  { value: "at_risk", label: "At Risk" },
  { value: "disrupted", label: "Disrupted" },
  { value: "rerouted", label: "Rerouted" },
  { value: "delivered", label: "Delivered" },
];

const RISK_OPTIONS = [
  { value: "", label: "All Risk Levels" },
  { value: "CRITICAL", label: "Critical" },
  { value: "HIGH", label: "High" },
  { value: "MEDIUM", label: "Medium" },
  { value: "LOW", label: "Low" },
];

const PRIORITY_OPTIONS = [
  { value: "", label: "All Priorities" },
  { value: "critical", label: "Critical" },
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
];

const FIRST_PAGE_SIZE = 20;
const NEXT_PAGE_SIZE = 25;

function priorityBadge(p: string) {
  switch (p) {
    case "critical": return "bg-red-500/20 text-red-300 border border-red-500/40";
    case "high": return "bg-amber-500/20 text-amber-300 border border-amber-500/40";
    case "medium": return "bg-blue-500/20 text-blue-300 border border-blue-500/40";
    default: return "bg-green-500/20 text-green-300 border border-green-500/40";
  }
}

function isOverdue(deadline: string) {
  return new Date(deadline) < new Date();
}

function formatDeadline(deadline: string) {
  const d = new Date(deadline);
  const now = new Date();
  const diff = d.getTime() - now.getTime();
  const hours = Math.round(diff / 3600000);
  if (hours < 0) return `${Math.abs(hours)}h overdue`;
  if (hours < 24) return `${hours}h left`;
  return `${Math.round(hours / 24)}d left`;
}

function ShipmentTable({
  shipments,
  onRefresh,
}: {
  shipments: Shipment[];
  onRefresh: () => void;
}) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [explanation, setExplanation] = useState<RiskExplanation | null>(null);
  const [loadingExplain, setLoadingExplain] = useState(false);
  const hoverTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [riskFilter, setRiskFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [deleting, setDeleting] = useState<string | null>(null);

  const handleMouseEnter = (id: string) => {
    if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
    hoverTimeout.current = setTimeout(() => {
      setHoveredId(id);
      setLoadingExplain(true);
      api.shipmentRiskExplain(id)
        .then(setExplanation)
        .catch(() => setExplanation(null))
        .finally(() => setLoadingExplain(false));
    }, 300);
  };

  const handleMouseLeave = () => {
    if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
    setHoveredId(null);
    setExplanation(null);
  };

  const handleDelete = async (id: string) => {
    if (!confirm(`Delete shipment ${id}? This cannot be undone.`)) return;
    setDeleting(id);
    try {
      await api.deleteShipment(id);
      onRefresh();
    } catch {
      alert("Failed to delete shipment");
    } finally {
      setDeleting(null);
    }
  };

  // Filter
  const filtered = shipments.filter((s) => {
    if (statusFilter && s.status !== statusFilter) return false;
    if (riskFilter && s.risk_level !== riskFilter) return false;
    if (priorityFilter && s.priority !== priorityFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      return (
        s.id.toLowerCase().includes(q) ||
        s.origin.city.toLowerCase().includes(q) ||
        s.destination.city.toLowerCase().includes(q) ||
        s.carrier.toLowerCase().includes(q) ||
        s.category.toLowerCase().includes(q)
      );
    }
    return true;
  });

  // Pagination: first page = 20, subsequent = 25
  const getPageSlice = (pageNum: number) => {
    if (pageNum === 0) return { start: 0, end: FIRST_PAGE_SIZE };
    const start = FIRST_PAGE_SIZE + (pageNum - 1) * NEXT_PAGE_SIZE;
    return { start, end: start + NEXT_PAGE_SIZE };
  };

  const totalPages = filtered.length <= FIRST_PAGE_SIZE
    ? 1
    : 1 + Math.ceil((filtered.length - FIRST_PAGE_SIZE) / NEXT_PAGE_SIZE);

  const { start, end } = getPageSlice(page);
  const paged = filtered.slice(start, end);

  // Reset page on filter change
  useEffect(() => { setPage(0); }, [statusFilter, riskFilter, priorityFilter, search]);

  return (
    <div className="bg-navy-800 border border-slate-700 rounded-xl overflow-hidden">
      <div className="px-5 py-3 border-b border-slate-700">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">All Shipments</h2>
          <span className="text-xs text-slate-500">{filtered.length} of {shipments.length} shipments · hover risk for details</span>
        </div>
        {/* Filters */}
        <div className="flex flex-wrap gap-3">
          <input
            type="text"
            placeholder="Search ID, city, carrier…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-navy-900 border border-slate-700 text-white placeholder-slate-500 rounded-lg px-3 py-1.5 text-sm w-52 focus:outline-none focus:border-blue-500"
          />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-navy-900 border border-slate-700 text-white rounded-lg px-3 py-1.5 text-sm focus:border-blue-500"
          >
            {STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            className="bg-navy-900 border border-slate-700 text-white rounded-lg px-3 py-1.5 text-sm focus:border-blue-500"
          >
            {RISK_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="bg-navy-900 border border-slate-700 text-white rounded-lg px-3 py-1.5 text-sm focus:border-blue-500"
          >
            {PRIORITY_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-slate-500 border-b border-slate-700/60">
              <th className="text-left px-5 py-2">ID</th>
              <th className="text-left px-3 py-2">Route</th>
              <th className="text-left px-3 py-2">Carrier</th>
              <th className="text-left px-3 py-2">Risk</th>
              <th className="text-left px-3 py-2">Priority</th>
              <th className="text-left px-3 py-2">Deadline</th>
              <th className="text-left px-3 py-2">Revenue</th>
              <th className="text-left px-3 py-2">Status</th>
              <th className="text-left px-3 py-2">Action</th>
            </tr>
          </thead>
          <tbody>
            {paged.map((s) => {
              const overdue = isOverdue(s.deadline);
              return (
                <tr
                  key={s.id}
                  className={`border-b border-slate-700/40 hover:bg-slate-800/40 transition-colors ${
                    overdue ? "bg-red-950/20" : ""
                  }`}
                >
                  <td className="px-5 py-3 font-mono text-blue-400 font-semibold">{s.id}</td>
                  <td className="px-3 py-3 text-slate-300">
                    <span className="text-slate-400">{s.origin.city}</span>
                    <span className="text-slate-600 mx-1">→</span>
                    <span>{s.destination.city}</span>
                  </td>
                  <td className="px-3 py-3 text-slate-400">{s.carrier}</td>
                  <td className="px-3 py-3">
                    <div
                      className="relative flex items-center gap-2 cursor-help"
                      onMouseEnter={() => handleMouseEnter(s.id)}
                      onMouseLeave={handleMouseLeave}
                    >
                      <span className={`font-bold ${riskColor(s.risk_level)}`}>{s.risk_score.toFixed(0)}</span>
                      <span className={`text-xs px-1.5 py-0.5 rounded ${riskBadge(s.risk_level)}`}>{s.risk_level}</span>
                      {hoveredId === s.id && !loadingExplain && (
                        <RiskTooltip explanation={explanation} visible={true} />
                      )}
                      {hoveredId === s.id && loadingExplain && (
                        <div className="absolute z-50 left-0 top-full mt-2 w-64 bg-navy-900 border border-slate-600 rounded-xl p-3 shadow-2xl">
                          <div className="text-xs text-slate-400 animate-pulse">Loading risk explanation…</div>
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-3 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${priorityBadge(s.priority)}`}>
                      {s.priority}
                    </span>
                  </td>
                  <td className="px-3 py-3">
                    <span className={`text-xs font-medium ${overdue ? "text-red-400 font-bold" : "text-slate-400"}`}>
                      {overdue && "⚠️ "}{formatDeadline(s.deadline)}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-slate-300">{formatINR(s.revenue)}</td>
                  <td className="px-3 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${
                      s.status === "disrupted" ? "bg-red-900/40 border-red-700 text-red-300"
                      : s.status === "at_risk" ? "bg-amber-900/40 border-amber-700 text-amber-300"
                      : s.status === "rerouted" ? "bg-blue-900/40 border-blue-700 text-blue-300"
                      : "bg-green-900/30 border-green-700 text-green-300"
                    }`}>{s.status}</span>
                  </td>
                  <td className="px-3 py-3 flex items-center gap-2">
                    {(s.status === "disrupted" || s.status === "at_risk") && (
                      <Link href={`/reroute/${s.id}`} className="text-xs text-blue-400 hover:text-blue-300 font-medium underline">
                        Reroute
                      </Link>
                    )}
                    <button
                      onClick={() => handleDelete(s.id)}
                      disabled={deleting === s.id}
                      className="text-xs text-red-400 hover:text-red-300 font-medium disabled:opacity-50"
                      title="Delete shipment"
                    >
                      {deleting === s.id ? "…" : "✕"}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {/* Pagination */}
      {totalPages > 1 && (
        <div className="px-5 py-3 border-t border-slate-700 flex items-center justify-between">
          <span className="text-xs text-slate-500">
            Page {page + 1} of {totalPages} · Showing {start + 1}–{Math.min(end, filtered.length)} of {filtered.length}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-3 py-1 text-xs rounded-lg bg-slate-700 text-white hover:bg-slate-600 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              ← Prev
            </button>
            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
              const pageNum = page < 3 ? i : page - 2 + i;
              if (pageNum >= totalPages) return null;
              return (
                <button
                  key={pageNum}
                  onClick={() => setPage(pageNum)}
                  className={`w-7 h-7 text-xs rounded-lg ${
                    pageNum === page
                      ? "bg-blue-600 text-white"
                      : "bg-slate-700 text-slate-300 hover:bg-slate-600"
                  }`}
                >
                  {pageNum + 1}
                </button>
              );
            })}
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="px-3 py-1 text-xs rounded-lg bg-slate-700 text-white hover:bg-slate-600 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Next →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Dashboard Page ─────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [kpis, setKpis] = useState<KPIData | null>(null);
  const [shipments, setShipments] = useState<Shipment[]>([]);
  const [disruptions, setDisruptions] = useState<Disruption[]>([]);
  const [topRisk, setTopRisk] = useState<TopRiskShipment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      // Rescore first to factor in disruptions/overdue
      await api.rescoreShipments().catch(() => {});
      const [k, s, d, tr] = await Promise.all([
        api.kpis(),
        api.shipments({ limit: 100 }),
        api.disruptions(),
        api.topRiskShipments(5),
      ]);
      setKpis(k);
      setShipments(s.shipments);
      setDisruptions(d.filter((x) => x.status === "active"));
      setTopRisk(tr);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // Auto-refresh every 60 seconds
    const iv = setInterval(loadData, 60000);
    return () => clearInterval(iv);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96 text-slate-400">
        <div className="text-center space-y-3">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p>Loading real-time supply chain data…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center space-y-3 max-w-md">
          <div className="text-red-400 text-lg font-semibold">Backend unreachable</div>
          <p className="text-slate-400 text-sm">{error}</p>
          <p className="text-slate-500 text-xs">
            Make sure the backend is running: <code className="text-blue-400">uvicorn main:app --port 8000</code>
          </p>
          <button onClick={() => window.location.reload()} className="mt-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-500">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Command Center</h1>
          <p className="text-slate-400 text-sm mt-0.5">Real-time Indian supply chain resilience dashboard · ML-powered risk scoring</p>
        </div>
        <Link href="/chat" className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">
          <span>🤖</span> Ask AI
        </Link>
      </div>

      {kpis && <KpiBar kpis={kpis} />}
      <DisruptionCards disruptions={disruptions} />
      <TopRiskPanel topRisk={topRisk} />
      <ShipmentTable shipments={shipments} onRefresh={loadData} />
    </div>
  );
}
