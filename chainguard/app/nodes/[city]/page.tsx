"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, NodeRiskAnalysis } from "@/lib/api";
import { riskBadge, riskColor } from "@/lib/utils";
import { DynamicMap, MapMarker } from "@/components/DynamicMap";
import Link from "next/link";

export default function NodeDetailPage() {
  const params = useParams();
  const city = decodeURIComponent(params.city as string);
  const [data, setData] = useState<NodeRiskAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.nodeRisk(city)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [city]);

  if (loading) return <div className="max-w-5xl mx-auto px-6 py-8 text-slate-400 animate-pulse">Loading risk analysis for {city}…</div>;
  if (error || !data) return <div className="max-w-5xl mx-auto px-6 py-8 text-red-400">Error: {error || "Node not found"}</div>;

  const mapMarkers: MapMarker[] = [
    { lat: data.lat, lng: data.lng, label: city, color: data.risk_score > 30 ? "red" : data.risk_score > 15 ? "amber" : "green", radius: 12, popup: `<b>${city}</b><br/>Risk: ${data.risk_score.toFixed(1)}` },
  ];

  const festImpact = data.festival_impact as { congestion?: number; festivals?: string[]; ecommerce?: string | null; monsoon?: boolean; is_peak_season?: boolean };

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-slate-400 mb-4">
        <Link href="/nodes" className="hover:text-blue-400">Nodes</Link>
        <span>→</span>
        <span className="text-white">{city}</span>
      </div>

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">{city}</h1>
          <p className="text-sm text-slate-400">{data.state} — Port/Hub Risk Analysis</p>
        </div>
        <span className={`px-4 py-1.5 rounded-full text-sm font-bold ${riskBadge(data.risk_level)}`}>
          {data.risk_level} — {data.risk_score.toFixed(1)}
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          {/* Map */}
          <div className="bg-navy-800 border border-slate-700 rounded-xl p-4">
            <DynamicMap markers={mapMarkers} height="250px" zoom={8} />
          </div>

          {/* Risk Factors */}
          <div className="bg-navy-800 border border-slate-700 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-300 mb-3">Risk Factors</h3>
            {data.risk_factors.length === 0 ? (
              <div className="text-slate-500 text-sm">No significant risk factors detected.</div>
            ) : (
              <div className="space-y-3">
                {data.risk_factors.map((f, i) => (
                  <div key={i} className="bg-navy-700/50 border border-slate-600 rounded-lg p-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-white">{f.name}</span>
                      <span className={`text-xs font-bold ${f.contribution > 0.3 ? "text-red-400" : f.contribution > 0.15 ? "text-amber-400" : "text-green-400"}`}>
                        {(f.contribution * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div className="text-xs text-slate-400">{f.detail}</div>
                    <div className="mt-1.5 bg-navy-700 rounded-full h-1.5 overflow-hidden">
                      <div className="h-full rounded-full bg-blue-500" style={{ width: `${Math.min(f.contribution * 100, 100)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Active Disruptions */}
          {data.active_disruptions.length > 0 && (
            <div className="bg-red-950/20 border border-red-800/50 rounded-xl p-5">
              <h3 className="text-sm font-semibold text-red-300 mb-3">Active Disruptions ({data.active_disruptions.length})</h3>
              <div className="space-y-2">
                {data.active_disruptions.map((d) => (
                  <div key={d.id} className="flex items-center justify-between bg-red-950/30 border border-red-700/40 rounded-lg p-3">
                    <div>
                      <span className="text-sm text-white font-mono">{d.id}</span>
                      <span className="ml-2 text-xs text-red-300 capitalize">{d.type}</span>
                    </div>
                    <span className="text-red-400 font-bold text-sm">{(d.severity * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Carriers */}
          <div className="bg-navy-800 border border-slate-700 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-300 mb-3">Carriers Operating ({data.carriers.length})</h3>
            <div className="flex flex-wrap gap-2">
              {data.carriers.map((c) => (
                <span key={c} className="bg-navy-700 border border-slate-600 text-slate-300 px-3 py-1 rounded-lg text-xs">{c}</span>
              ))}
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Metrics */}
          <div className="bg-navy-800 border border-slate-700 rounded-xl p-5 space-y-3">
            <h3 className="text-sm font-semibold text-slate-300 mb-1">Key Metrics</h3>
            <Metric label="Throughput Rank" value={`#${data.throughput_rank} of 20`} />
            <Metric label="Total Shipments" value={String(data.total_shipments_through)} />
            <Metric label="Network Degree" value={String(data.degree)} />
            <Metric label="Resilience Score" value={`${(data.resilience_score ?? 0).toFixed(1)}/100`} color={(data.resilience_score ?? 0) >= 70 ? "text-green-400" : (data.resilience_score ?? 0) >= 50 ? "text-amber-400" : "text-red-400"} />
            <Metric label="Bottleneck Score" value={(data.bottleneck_score ?? 0).toFixed(2)} color={(data.bottleneck_score ?? 0) > 0.7 ? "text-red-400" : "text-green-400"} />
          </div>

          {/* Weather */}
          {data.weather && (
            <div className="bg-navy-800 border border-slate-700 rounded-xl p-5">
              <h3 className="text-sm font-semibold text-slate-300 mb-3">🌤️ Weather</h3>
              <div className="space-y-1 text-xs text-slate-300">
                {Object.entries(data.weather).map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <span className="text-slate-500 capitalize">{k.replace(/_/g, " ")}</span>
                    <span>{typeof v === "number" ? (v as number).toFixed(1) : String(v)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Festival Impact */}
          <div className="bg-navy-800 border border-slate-700 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-300 mb-3">🎉 Festival & Seasonal Impact</h3>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between"><span className="text-slate-500">Congestion</span><span className={festImpact.congestion && festImpact.congestion > 0 ? "text-amber-400" : "text-green-400"}>{festImpact.congestion ? `+${(festImpact.congestion * 100).toFixed(0)}%` : "None"}</span></div>
              {festImpact.festivals && festImpact.festivals.length > 0 && (
                <div><span className="text-purple-300">{festImpact.festivals.join(", ")}</span></div>
              )}
              {festImpact.ecommerce && <div className="text-amber-300">🛒 {festImpact.ecommerce}</div>}
              {festImpact.monsoon && <div className="text-blue-300">🌧️ Monsoon season</div>}
              {festImpact.is_peak_season && <div className="text-red-300">🔥 Peak season</div>}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="bg-navy-800 border border-slate-700 rounded-xl p-5 space-y-2">
            <h3 className="text-sm font-semibold text-slate-300 mb-1">Quick Actions</h3>
            <Link href={`/simulate?node=${encodeURIComponent(city)}`} className="block w-full text-center bg-red-600/20 hover:bg-red-600/30 border border-red-700/50 text-red-300 py-2 rounded-lg text-xs font-medium transition-colors">
              🔥 Simulate Disruption
            </Link>
            <Link href={`/create?origin=${encodeURIComponent(city)}`} className="block w-full text-center bg-blue-600/20 hover:bg-blue-600/30 border border-blue-700/50 text-blue-300 py-2 rounded-lg text-xs font-medium transition-colors">
              📦 Create Shipment from Here
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value, color = "text-white" }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-slate-500">{label}</span>
      <span className={`text-sm font-bold ${color}`}>{value}</span>
    </div>
  );
}
