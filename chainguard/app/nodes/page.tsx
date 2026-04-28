"use client";
import { useEffect, useState } from "react";
import { api, NodeSummary, FestivalData } from "@/lib/api";
import { riskBadge } from "@/lib/utils";
import { DynamicMap, MapMarker } from "@/components/DynamicMap";
import Link from "next/link";

export default function NodesPage() {
  const [nodes, setNodes] = useState<NodeSummary[]>([]);
  const [festivals, setFestivals] = useState<FestivalData | null>(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<"map" | "table">("map");

  useEffect(() => {
    Promise.all([api.nodes(), api.festivals()])
      .then(([n, f]) => { setNodes(n); setFestivals(f); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const mapMarkers: MapMarker[] = nodes.map((n) => {
    const col = n.avg_risk_score > 30 ? "red" : n.avg_risk_score > 15 ? "amber" : n.is_bottleneck ? "cyan" : "green";
    return {
      lat: n.lat,
      lng: n.lng,
      label: n.city,
      color: col,
      radius: Math.max(4, Math.min(12, n.shipment_count)),
      popup: `<b>${n.city}</b>, ${n.state}<br/>Shipments: ${n.shipment_count}<br/>Risk: ${n.avg_risk_score.toFixed(1)} (${n.risk_level})<br/>Disruptions: ${n.disruption_count}<br/>Connections: ${n.degree}${n.is_bottleneck ? "<br/><b>⚠️ Bottleneck</b>" : ""}`,
    };
  });

  if (loading) return <div className="max-w-7xl mx-auto px-6 py-8 text-slate-400 animate-pulse">Loading network nodes…</div>;

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Network Nodes</h1>
          <p className="text-sm text-slate-400">{nodes.length} logistics hubs across India — click a node for detailed risk analysis.</p>
        </div>
        <div className="flex gap-1 bg-navy-800 border border-slate-700 rounded-lg p-0.5">
          <button onClick={() => setView("map")} className={`px-3 py-1 rounded text-xs font-medium transition-colors ${view === "map" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"}`}>Map</button>
          <button onClick={() => setView("table")} className={`px-3 py-1 rounded text-xs font-medium transition-colors ${view === "table" ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"}`}>Table</button>
        </div>
      </div>

      {/* Festival banner */}
      {festivals && (festivals.active_today.length > 0 || festivals.ecommerce_surge || festivals.monsoon) && (
        <div className="bg-purple-950/30 border border-purple-800/50 rounded-xl p-4 mb-4 flex items-center gap-4 flex-wrap text-sm">
          {festivals.active_today.map((f) => <span key={f.name} className="bg-purple-900/50 text-purple-300 px-2 py-1 rounded text-xs">🎉 {f.name} (+{(f.congestion_factor * 100).toFixed(0)}% congestion)</span>)}
          {festivals.ecommerce_surge && <span className="bg-amber-900/50 text-amber-300 px-2 py-1 rounded text-xs">🛒 {festivals.ecommerce_surge.name}</span>}
          {festivals.monsoon && <span className="bg-blue-900/50 text-blue-300 px-2 py-1 rounded text-xs">🌧️ Monsoon Season</span>}
        </div>
      )}

      {view === "map" && (
        <div className="bg-navy-800 border border-slate-700 rounded-xl p-4 mb-6">
          <DynamicMap markers={mapMarkers} height="500px" />
        </div>
      )}

      {/* Nodes table */}
      <div className="bg-navy-800 border border-slate-700 rounded-xl overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-slate-500 text-xs border-b border-slate-700 uppercase">
              <th className="text-left py-3 px-4">Node</th>
              <th className="text-center py-3 px-2">Shipments</th>
              <th className="text-center py-3 px-2">Risk</th>
              <th className="text-center py-3 px-2">Disruptions</th>
              <th className="text-center py-3 px-2">Connections</th>
              <th className="text-center py-3 px-2">Festival</th>
              <th className="text-center py-3 px-2">Status</th>
              <th className="text-center py-3 px-2">Action</th>
            </tr>
          </thead>
          <tbody>
            {nodes.map((n) => (
              <tr key={n.city} className="border-b border-slate-700/50 hover:bg-navy-700/30 transition-colors">
                <td className="py-3 px-4">
                  <div className="font-medium text-white">{n.city}</div>
                  <div className="text-xs text-slate-500">{n.state}</div>
                </td>
                <td className="text-center py-3 px-2 text-white">{n.shipment_count}</td>
                <td className="text-center py-3 px-2">
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${riskBadge(n.risk_level)}`}>
                    {n.avg_risk_score.toFixed(1)}
                  </span>
                </td>
                <td className="text-center py-3 px-2">
                  {n.disruption_count > 0 ? <span className="text-red-400 font-bold">{n.disruption_count}</span> : <span className="text-slate-500">0</span>}
                </td>
                <td className="text-center py-3 px-2 text-slate-300">{n.degree}</td>
                <td className="text-center py-3 px-2">
                  {n.festival_congestion > 0 ? <span className="text-purple-400">{(n.festival_congestion * 100).toFixed(0)}%</span> : <span className="text-slate-500">—</span>}
                </td>
                <td className="text-center py-3 px-2">
                  <div className="flex items-center justify-center gap-1">
                    {n.is_bottleneck && <span className="text-[10px] bg-amber-900/40 text-amber-300 px-1.5 py-0.5 rounded">Bottleneck</span>}
                    {n.monsoon && <span className="text-[10px] bg-blue-900/40 text-blue-300 px-1.5 py-0.5 rounded">🌧️</span>}
                    {n.active_festivals.length > 0 && <span className="text-[10px] bg-purple-900/40 text-purple-300 px-1.5 py-0.5 rounded">🎉</span>}
                  </div>
                </td>
                <td className="text-center py-3 px-2">
                  <Link href={`/nodes/${encodeURIComponent(n.city)}`} className="text-blue-400 hover:text-blue-300 text-xs font-medium">
                    Details →
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
