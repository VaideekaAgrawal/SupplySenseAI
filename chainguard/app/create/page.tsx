"use client";
import { useState } from "react";
import { api, CreateShipmentResponse } from "@/lib/api";
import { formatINR, riskColor, riskBadge } from "@/lib/utils";
import { DynamicMap, MapMarker, MapRoute } from "@/components/DynamicMap";

const CITIES = [
  "Delhi","Mumbai","Bangalore","Hyderabad","Chennai","Kolkata","Pune","Ahmedabad",
  "Jaipur","Lucknow","Surat","Nagpur","Kochi","Coimbatore","Chandigarh","Patna",
  "Visakhapatnam","Bhopal","Indore","Nhava Sheva",
];
const CARRIERS = ["BlueDart","Delhivery","DHL Express","FedEx India","DTDC","Ecom Express","Shadowfax","XpressBees"];
const MODES = ["First Class","Second Class","Same Day","Standard Class"];
const CATEGORIES = ["Electronics","Pharmaceuticals","FMCG","Textiles","Auto Parts","Perishables","Machinery","General"];

export default function CreateShipmentPage() {
  const [form, setForm] = useState({
    origin_city: "Delhi",
    destination_city: "Mumbai",
    carrier: "BlueDart",
    shipping_mode: "First Class",
    category: "Electronics",
    revenue: 50000,
    deadline_hours: 72,
  });
  const [result, setResult] = useState<CreateShipmentResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (form.origin_city === form.destination_city) {
      setError("Origin and destination must differ.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const r = await api.createShipment(form);
      setResult(r);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create shipment");
    } finally {
      setLoading(false);
    }
  };

  const mapMarkers: MapMarker[] = result
    ? [
        { lat: result.shipment.origin.lat, lng: result.shipment.origin.lng, label: result.shipment.origin.city, color: "cyan", radius: 8, popup: `<b>Origin:</b> ${result.shipment.origin.city}` },
        { lat: result.shipment.destination.lat, lng: result.shipment.destination.lng, label: result.shipment.destination.city, color: "green", radius: 8, popup: `<b>Dest:</b> ${result.shipment.destination.city}` },
      ]
    : [];

  const mapRoutes: MapRoute[] = result
    ? result.routes.map((rt, i) => ({
        waypoints: rt.waypoints,
        color: i === 0 ? "cyan" : i === 1 ? "amber" : "purple",
        weight: rt.is_recommended ? 4 : 2,
        dashArray: rt.is_recommended ? undefined : "8 4",
        label: rt.name,
      }))
    : [];

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <h1 className="text-2xl font-bold text-white mb-1">Create Shipment</h1>
      <p className="text-sm text-slate-400 mb-6">Enter shipment details to get instant risk analysis and route recommendations.</p>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Form */}
        <div className="lg:col-span-1 bg-navy-800 border border-slate-700 rounded-xl p-6 space-y-4">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Origin City</label>
            <select value={form.origin_city} onChange={(e) => setForm({ ...form, origin_city: e.target.value })} className="w-full bg-navy-700 border border-slate-600 text-white rounded-lg px-3 py-2 text-sm focus:ring-blue-500 focus:border-blue-500">
              {CITIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Destination City</label>
            <select value={form.destination_city} onChange={(e) => setForm({ ...form, destination_city: e.target.value })} className="w-full bg-navy-700 border border-slate-600 text-white rounded-lg px-3 py-2 text-sm focus:ring-blue-500 focus:border-blue-500">
              {CITIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Carrier</label>
              <select value={form.carrier} onChange={(e) => setForm({ ...form, carrier: e.target.value })} className="w-full bg-navy-700 border border-slate-600 text-white rounded-lg px-3 py-2 text-sm">
                {CARRIERS.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Shipping Mode</label>
              <select value={form.shipping_mode} onChange={(e) => setForm({ ...form, shipping_mode: e.target.value })} className="w-full bg-navy-700 border border-slate-600 text-white rounded-lg px-3 py-2 text-sm">
                {MODES.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Category</label>
            <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="w-full bg-navy-700 border border-slate-600 text-white rounded-lg px-3 py-2 text-sm">
              {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Revenue (₹)</label>
              <input type="number" value={form.revenue} onChange={(e) => setForm({ ...form, revenue: Number(e.target.value) })} className="w-full bg-navy-700 border border-slate-600 text-white rounded-lg px-3 py-2 text-sm" min={0} />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Deadline (hrs)</label>
              <input type="number" value={form.deadline_hours} onChange={(e) => setForm({ ...form, deadline_hours: Number(e.target.value) })} className="w-full bg-navy-700 border border-slate-600 text-white rounded-lg px-3 py-2 text-sm" min={1} />
            </div>
          </div>

          {error && <div className="text-red-400 text-sm bg-red-950/30 border border-red-800/50 rounded-lg p-3">{error}</div>}

          <button onClick={submit} disabled={loading} className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-semibold py-2.5 rounded-lg transition-colors text-sm">
            {loading ? "Analyzing…" : "Create & Analyze"}
          </button>
        </div>

        {/* Results */}
        <div className="lg:col-span-2 space-y-4">
          {!result && !loading && (
            <div className="bg-navy-800 border border-slate-700 rounded-xl p-12 text-center text-slate-500">
              <div className="text-4xl mb-3">📦</div>
              <div className="text-lg font-medium">Configure your shipment</div>
              <div className="text-sm mt-1">Fill in details and click &ldquo;Create &amp; Analyze&rdquo; to get risk scoring and optimal routes.</div>
            </div>
          )}

          {loading && (
            <div className="bg-navy-800 border border-slate-700 rounded-xl p-12 text-center text-slate-400 animate-pulse">
              <div className="text-4xl mb-3">🔄</div>
              Analyzing risk factors and computing routes…
            </div>
          )}

          {result && (
            <>
              {/* Risk Overview */}
              <div className="bg-navy-800 border border-slate-700 rounded-xl p-5">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-lg font-semibold text-white">Risk Analysis — {result.shipment.id}</h2>
                    <p className="text-xs text-slate-400">{result.shipment.origin.city} → {result.shipment.destination.city} • {result.shipment.carrier} • {result.shipment.shipping_mode}</p>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-xs font-bold ${riskBadge(result.risk_breakdown.risk_level)}`}>
                    {result.risk_breakdown.risk_level} — {result.risk_breakdown.risk_score.toFixed(1)}
                  </span>
                </div>

                {/* Risk Factors */}
                <div className="space-y-2">
                  {result.risk_breakdown.top_factors.map((f, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <div className="w-32 text-xs text-slate-400 truncate">{f.name}</div>
                      <div className="flex-1 bg-navy-700 rounded-full h-2 overflow-hidden">
                        <div className="h-full rounded-full bg-blue-500" style={{ width: `${Math.min(f.contribution * 100, 100)}%` }} />
                      </div>
                      <div className="w-12 text-xs text-slate-300 text-right">{(f.contribution * 100).toFixed(0)}%</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Map */}
              <div className="bg-navy-800 border border-slate-700 rounded-xl p-4">
                <h3 className="text-sm font-semibold text-slate-300 mb-3">Route Map</h3>
                <DynamicMap markers={mapMarkers} routes={mapRoutes} height="350px" />
              </div>

              {/* Route Alternatives */}
              <div className="bg-navy-800 border border-slate-700 rounded-xl p-5">
                <h3 className="text-sm font-semibold text-slate-300 mb-3">Route Alternatives ({result.routes.length})</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {result.routes.map((rt) => (
                    <div key={rt.id} className={`border rounded-xl p-4 ${rt.is_recommended ? "border-cyan-600 bg-cyan-950/20" : "border-slate-700 bg-navy-700/30"}`}>
                      {rt.is_recommended && <div className="text-[10px] text-cyan-400 font-bold uppercase mb-1">⭐ Recommended</div>}
                      <div className="font-medium text-white text-sm">{rt.name}</div>
                      <div className="text-xs text-slate-400 mt-1 mb-3">{rt.description}</div>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div><span className="text-slate-500">Time:</span> <span className="text-white">{rt.time_hours.toFixed(0)}h</span></div>
                        <div><span className="text-slate-500">Cost:</span> <span className="text-white">{formatINR(rt.cost_inr)}</span></div>
                        <div><span className="text-slate-500">Risk:</span> <span className={riskColor(rt.risk_score > 30 ? "HIGH" : rt.risk_score > 15 ? "MEDIUM" : "LOW")}>{rt.risk_score.toFixed(1)}</span></div>
                        <div><span className="text-slate-500">CO₂:</span> <span className="text-white">{rt.carbon_kg.toFixed(0)}kg</span></div>
                      </div>
                      {rt.recommendation_reason && <div className="text-[10px] text-slate-400 mt-2 italic">{rt.recommendation_reason}</div>}
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
