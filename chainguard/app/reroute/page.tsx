"use client";
import { useEffect, useState, useCallback } from "react";
import { api, Shipment, ShipmentListResponse } from "@/lib/api";
import Link from "next/link";
import { formatINR, riskBadge, riskColor } from "@/lib/utils";

const PAGE_SIZE = 10;

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

export default function RerouteIndexPage() {
  const [shipments, setShipments] = useState<Shipment[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [statusFilter, setStatusFilter] = useState("");
  const [riskFilter, setRiskFilter] = useState("");
  const [search, setSearch] = useState("");

  const fetchShipments = useCallback(async () => {
    setLoading(true);
    try {
      const params: { status?: string; risk_level?: string; limit: number; offset: number } = {
        limit: 100,
        offset: 0,
      };
      if (statusFilter) params.status = statusFilter;
      if (riskFilter) params.risk_level = riskFilter;
      const r: ShipmentListResponse = await api.shipments(params);
      setShipments(r.shipments);
    } catch {
      setShipments([]);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, riskFilter]);

  useEffect(() => { fetchShipments(); }, [fetchShipments]);
  useEffect(() => { setPage(0); }, [statusFilter, riskFilter, search]);

  const filtered = shipments.filter((s) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      s.id.toLowerCase().includes(q) ||
      s.origin.city.toLowerCase().includes(q) ||
      s.destination.city.toLowerCase().includes(q) ||
      s.carrier.toLowerCase().includes(q) ||
      s.category.toLowerCase().includes(q)
    );
  });

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  if (loading) return (
    <div className="flex items-center justify-center h-64 text-slate-400 animate-pulse">Loading shipments…</div>
  );

  return (
    <div className="max-w-5xl mx-auto px-6 py-6">
      <h1 className="text-2xl font-bold text-white mb-1">Route Optimization</h1>
      <p className="text-slate-400 text-sm mb-5">Browse all shipments and select one to view and accept route alternatives.</p>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-5">
        <input
          type="text"
          placeholder="Search ID, city, carrier…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="bg-navy-800 border border-slate-700 text-white placeholder-slate-500 rounded-lg px-3 py-2 text-sm w-52 focus:outline-none focus:border-blue-500"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-navy-800 border border-slate-700 text-white rounded-lg px-3 py-2 text-sm focus:border-blue-500"
        >
          {STATUS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        <select
          value={riskFilter}
          onChange={(e) => setRiskFilter(e.target.value)}
          className="bg-navy-800 border border-slate-700 text-white rounded-lg px-3 py-2 text-sm focus:border-blue-500"
        >
          {RISK_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        <div className="ml-auto text-sm text-slate-500 self-center">
          {filtered.length} shipment{filtered.length !== 1 ? "s" : ""}
        </div>
      </div>

      {/* List */}
      <div className="space-y-2 max-h-[60vh] overflow-y-auto pr-1">
        {paged.map((s) => (
          <Link key={s.id} href={`/reroute/${s.id}`}
            className="block bg-navy-800 border border-slate-700 hover:border-blue-600 rounded-xl p-4 transition-colors">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3 min-w-0">
                <span className="font-mono font-bold text-blue-400 text-sm">{s.id}</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded ${riskBadge(s.risk_level)}`}>{s.risk_level}</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded-full border ${
                  s.status === "disrupted" ? "bg-red-900/40 border-red-700 text-red-300"
                  : s.status === "at_risk" ? "bg-amber-900/40 border-amber-700 text-amber-300"
                  : s.status === "rerouted" ? "bg-blue-900/40 border-blue-700 text-blue-300"
                  : "bg-green-900/30 border-green-700 text-green-300"
                }`}>{s.status.replace("_", " ")}</span>
                <span className="text-sm text-slate-400 truncate">
                  {s.origin.city} → {s.destination.city}
                </span>
                <span className="text-xs text-slate-500 hidden sm:inline">· {s.carrier} · {s.category}</span>
              </div>
              <div className="flex items-center gap-4 shrink-0">
                <span className="text-xs text-slate-500">{formatINR(s.revenue)}</span>
                <span className={`font-bold text-lg ${riskColor(s.risk_level)}`}>{s.risk_score.toFixed(0)}</span>
              </div>
            </div>
          </Link>
        ))}
        {filtered.length === 0 && (
          <div className="text-slate-400 text-center py-8">No shipments match your filters.</div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-5">
          <button
            onClick={() => setPage(Math.max(0, page - 1))}
            disabled={page === 0}
            className="px-3 py-1.5 bg-navy-800 border border-slate-700 text-slate-300 rounded-lg text-xs disabled:opacity-30 hover:border-blue-600 transition-colors"
          >
            ← Prev
          </button>
          <span className="text-xs text-slate-500">
            Page {page + 1} of {totalPages}
          </span>
          <button
            onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
            disabled={page >= totalPages - 1}
            className="px-3 py-1.5 bg-navy-800 border border-slate-700 text-slate-300 rounded-lg text-xs disabled:opacity-30 hover:border-blue-600 transition-colors"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
