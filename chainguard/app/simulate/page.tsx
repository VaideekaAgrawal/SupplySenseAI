"use client";
import { useState, useEffect } from "react";
import { api, NodeSummary, SimulateNodeResponse } from "@/lib/api";
import { formatINR, riskBadge } from "@/lib/utils";
import { DynamicMap, MapMarker } from "@/components/DynamicMap";

const DISRUPTION_TYPES = [
  { value: "congestion", label: "Port Congestion", icon: "🚢" },
  { value: "weather", label: "Severe Weather", icon: "🌧️" },
  { value: "strike", label: "Worker Strike", icon: "✊" },
  { value: "infrastructure", label: "Infrastructure Failure", icon: "🛤️" },
  { value: "flood", label: "Flood", icon: "🌊" },
  { value: "earthquake", label: "Earthquake", icon: "🔴" },
  { value: "cyber_attack", label: "Cyber Attack", icon: "💻" },
];

export default function SimulatePage() {
  const [nodes, setNodes] = useState<NodeSummary[]>([]);
  const [form, setForm] = useState({ node: "Mumbai", disruption_type: "congestion", severity: 0.7, duration_hours: 48 });
  const [result, setResult] = useState<SimulateNodeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.nodes().then(setNodes).catch(() => {});
  }, []);

  const simulate = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await api.simulateNode(form);
      setResult(r);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Simulation failed");
    } finally {
      setLoading(false);
    }
  };

  const selectedNode = nodes.find((n) => n.city === form.node);

  const mapMarkers: MapMarker[] = result
    ? [
        { lat: selectedNode?.lat || 20, lng: selectedNode?.lng || 78, label: form.node, color: "red", radius: 12, popup: `<b>Disruption:</b> ${form.node}<br/>Severity: ${(form.severity * 100).toFixed(0)}%` },
        ...result.affected_shipments.map((s) => {
          const dest = s.route.split("→")[1]?.trim();
          const node = nodes.find((n) => n.city === dest);
          return node
            ? { lat: node.lat, lng: node.lng, label: dest, color: "amber", radius: 6, popup: `<b>${s.id}</b>: ${s.route}<br/>Risk: ${s.risk_score.toFixed(1)}<br/>Revenue: ${formatINR(s.revenue)}` }
            : null;
        }).filter(Boolean) as MapMarker[],
      ]
    : nodes.map((n) => ({
        lat: n.lat,
        lng: n.lng,
        label: n.city,
        color: n.city === form.node ? "red" : n.is_bottleneck ? "amber" : "slate",
        radius: n.city === form.node ? 10 : n.is_bottleneck ? 7 : 5,
        popup: `<b>${n.city}</b><br/>${n.shipment_count} shipments • ${n.disruption_count} disruptions`,
      }));

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold text-white mb-1">What-If Simulation</h1>
      <p className="text-sm text-slate-400 mb-6">Simulate disruptions at any node and see cascade impact on your supply chain.</p>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Controls */}
        <div className="lg:col-span-1 space-y-4">
          <div className="bg-navy-800 border border-slate-700 rounded-xl p-6 space-y-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Target Node</label>
              <select value={form.node} onChange={(e) => setForm({ ...form, node: e.target.value })} className="w-full bg-navy-700 border border-slate-600 text-white rounded-lg px-3 py-2 text-sm">
                {nodes.map((n) => (
                  <option key={n.city} value={n.city}>
                    {n.city} ({n.shipment_count} shipments{n.is_bottleneck ? " • Bottleneck" : ""})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs text-slate-400 mb-1">Disruption Type</label>
              <div className="grid grid-cols-2 gap-2">
                {DISRUPTION_TYPES.map((dt) => (
                  <button key={dt.value} onClick={() => setForm({ ...form, disruption_type: dt.value })}
                    className={`text-left px-3 py-2 rounded-lg text-xs border transition-colors ${form.disruption_type === dt.value ? "border-blue-500 bg-blue-950/40 text-blue-300" : "border-slate-700 bg-navy-700/30 text-slate-400 hover:border-slate-600"}`}>
                    <span className="mr-1">{dt.icon}</span> {dt.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs text-slate-400 mb-1">Severity: {(form.severity * 100).toFixed(0)}%</label>
              <input type="range" min={0.1} max={1} step={0.05} value={form.severity} onChange={(e) => setForm({ ...form, severity: Number(e.target.value) })}
                className="w-full accent-red-500" />
              <div className="flex justify-between text-[10px] text-slate-500 mt-0.5">
                <span>Minor</span><span>Moderate</span><span>Severe</span><span>Critical</span>
              </div>
            </div>

            <div>
              <label className="block text-xs text-slate-400 mb-1">Duration: {form.duration_hours}h</label>
              <input type="range" min={6} max={168} step={6} value={form.duration_hours} onChange={(e) => setForm({ ...form, duration_hours: Number(e.target.value) })}
                className="w-full accent-amber-500" />
              <div className="flex justify-between text-[10px] text-slate-500 mt-0.5">
                <span>6h</span><span>3d</span><span>1w</span>
              </div>
            </div>

            {error && <div className="text-red-400 text-sm bg-red-950/30 border border-red-800/50 rounded-lg p-3">{error}</div>}

            <button onClick={simulate} disabled={loading}
              className="w-full bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white font-semibold py-2.5 rounded-lg transition-colors text-sm">
              {loading ? "Simulating…" : "🔥 Run Simulation"}
            </button>
          </div>

          {/* Node info card */}
          {selectedNode && (
            <div className="bg-navy-800 border border-slate-700 rounded-xl p-4 space-y-2">
              <div className="text-sm font-semibold text-white">{selectedNode.city}, {selectedNode.state}</div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div><span className="text-slate-500">Shipments:</span> <span className="text-white">{selectedNode.shipment_count}</span></div>
                <div><span className="text-slate-500">Disruptions:</span> <span className="text-white">{selectedNode.disruption_count}</span></div>
                <div><span className="text-slate-500">Avg Risk:</span> <span className="text-white">{selectedNode.avg_risk_score.toFixed(1)}</span></div>
                <div><span className="text-slate-500">Connections:</span> <span className="text-white">{selectedNode.degree}</span></div>
              </div>
              {selectedNode.is_bottleneck && <div className="text-[10px] bg-amber-900/30 text-amber-300 px-2 py-1 rounded">⚠️ Network bottleneck — high connectivity</div>}
              {selectedNode.monsoon && <div className="text-[10px] bg-blue-900/30 text-blue-300 px-2 py-1 rounded">🌧️ Monsoon season active</div>}
              {selectedNode.active_festivals.length > 0 && <div className="text-[10px] bg-purple-900/30 text-purple-300 px-2 py-1 rounded">🎉 Festivals: {selectedNode.active_festivals.join(", ")}</div>}
            </div>
          )}
        </div>

        {/* Results */}
        <div className="lg:col-span-2 space-y-4">
          {/* Map */}
          <div className="bg-navy-800 border border-slate-700 rounded-xl p-4">
            <h3 className="text-sm font-semibold text-slate-300 mb-3">Network Impact Map</h3>
            <DynamicMap markers={mapMarkers} height="300px" />
          </div>

          {!result && !loading && (
            <div className="bg-navy-800 border border-slate-700 rounded-xl p-12 text-center text-slate-500">
              <div className="text-4xl mb-3">🧪</div>
              <div className="text-lg font-medium">Configure a scenario</div>
              <div className="text-sm mt-1">Select a node, disruption type, and severity to see the predicted cascade impact.</div>
            </div>
          )}

          {result && (
            <>
              {/* Impact KPIs */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-red-950/30 border border-red-800/60 rounded-xl p-4">
                  <div className="text-xs text-red-300/70">Shipments Affected</div>
                  <div className="text-2xl font-bold text-red-400">{result.affected_shipments.length}</div>
                </div>
                <div className="bg-red-950/30 border border-red-800/60 rounded-xl p-4">
                  <div className="text-xs text-red-300/70">Revenue at Risk</div>
                  <div className="text-2xl font-bold text-red-400">{formatINR(result.revenue_at_risk)}</div>
                </div>
                <div className="bg-amber-950/30 border border-amber-800/60 rounded-xl p-4">
                  <div className="text-xs text-amber-300/70">Duration</div>
                  <div className="text-2xl font-bold text-amber-400">{result.duration_hours}h</div>
                </div>
                <div className="bg-green-950/30 border border-green-800/60 rounded-xl p-4">
                  <div className="text-xs text-green-300/70">Alt Routes Available</div>
                  <div className="text-2xl font-bold text-green-400">{result.alternative_routes_available}</div>
                </div>
              </div>

              {/* Recommendations */}
              <div className="bg-navy-800 border border-slate-700 rounded-xl p-5">
                <h3 className="text-sm font-semibold text-slate-300 mb-3">🛡️ Mitigation Recommendations</h3>
                <div className="space-y-2">
                  {result.recommendations.map((r, i) => (
                    <div key={i} className="flex items-start gap-2 text-sm text-slate-300 bg-navy-700/50 border border-slate-600 rounded-lg p-3">
                      <span className="text-green-400 mt-0.5">✓</span>
                      <span>{r}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Affected shipments table */}
              {result.affected_shipments.length > 0 && (
                <div className="bg-navy-800 border border-slate-700 rounded-xl p-5 overflow-x-auto">
                  <h3 className="text-sm font-semibold text-slate-300 mb-3">Affected Shipments ({result.affected_shipments.length})</h3>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-slate-500 text-xs border-b border-slate-700">
                        <th className="text-left py-2 px-2">ID</th>
                        <th className="text-left py-2 px-2">Route</th>
                        <th className="text-right py-2 px-2">Revenue</th>
                        <th className="text-right py-2 px-2">Risk</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.affected_shipments.map((s) => (
                        <tr key={s.id} className="border-b border-slate-700/50 hover:bg-navy-700/30">
                          <td className="py-2 px-2 text-white font-mono">{s.id}</td>
                          <td className="py-2 px-2 text-slate-300">{s.route}</td>
                          <td className="py-2 px-2 text-right text-slate-300">{formatINR(s.revenue)}</td>
                          <td className="py-2 px-2 text-right text-amber-400">{s.risk_score.toFixed(1)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
