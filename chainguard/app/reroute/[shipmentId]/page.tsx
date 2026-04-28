"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, OptimizeResponse, RouteOption, Shipment } from "@/lib/api";
import { formatINR, riskColor } from "@/lib/utils";

// ── Weight Sliders ─────────────────────────────────────────────────────────────

interface Weights { cost: number; time: number; carbon: number; risk: number; }

function WeightSliders({ weights, onChange }: { weights: Weights; onChange: (w: Weights) => void }) {
  const labels: { key: keyof Weights; label: string; color: string }[] = [
    { key: "cost", label: "Cost", color: "accent-blue-500" },
    { key: "time", label: "Speed", color: "accent-cyan-500" },
    { key: "carbon", label: "Carbon", color: "accent-green-500" },
    { key: "risk", label: "Safety", color: "accent-red-500" },
  ];

  return (
    <div className="bg-navy-800 border border-slate-700 rounded-xl p-5 mb-5">
      <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">
        Optimization Weights
      </h3>
      <div className="space-y-4">
        {labels.map(({ key, label }) => (
          <div key={key}>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-400">{label}</span>
              <span className="text-slate-300 font-medium">{Math.round(weights[key] * 100)}%</span>
            </div>
            <input
              type="range" min={0} max={100} step={5}
              value={Math.round(weights[key] * 100)}
              onChange={(e) => {
                const v = Number(e.target.value) / 100;
                onChange({ ...weights, [key]: v });
              }}
              className="w-full h-1.5 bg-slate-700 rounded-full cursor-pointer"
            />
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Route Option Card ──────────────────────────────────────────────────────────

function RouteCard({
  route, onAccept, accepted
}: {
  route: RouteOption; onAccept: (id: string) => void; accepted: boolean;
}) {
  const riskLabel = route.risk_score < 20 ? "LOW" : route.risk_score < 45 ? "MEDIUM" : route.risk_score < 70 ? "HIGH" : "CRITICAL";

  return (
    <div className={`border rounded-xl p-5 transition-all ${
      route.is_recommended
        ? "border-blue-600 bg-blue-950/30 glow-blue"
        : accepted
        ? "border-green-600 bg-green-950/20"
        : "border-slate-700 bg-navy-800"
    }`}>
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-semibold text-white">{route.name}</span>
            {route.is_recommended && (
              <span className="text-xs bg-blue-600/30 text-blue-300 border border-blue-600/50 px-2 py-0.5 rounded-full">
                RECOMMENDED
              </span>
            )}
            {accepted && (
              <span className="text-xs bg-green-600/30 text-green-300 border border-green-600/50 px-2 py-0.5 rounded-full">
                ACCEPTED ✓
              </span>
            )}
          </div>
          <p className="text-sm text-slate-400 mt-0.5">{route.description}</p>
        </div>
        <div className="text-right text-sm font-bold text-slate-300">
          #{route.id}
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        {[
          { label: "Time", value: `${route.time_hours.toFixed(1)}h`, color: "text-cyan-400" },
          { label: "Cost", value: formatINR(route.cost_inr), color: "text-blue-300" },
          { label: "Carbon", value: `${route.carbon_kg.toFixed(0)} kg`, color: "text-green-400" },
          { label: "Risk", value: `${route.risk_score.toFixed(0)}%`, color: riskColor(riskLabel) },
        ].map((m) => (
          <div key={m.label} className="bg-slate-800/50 rounded-lg p-2 text-center">
            <div className={`font-bold text-base ${m.color}`}>{m.value}</div>
            <div className="text-xs text-slate-500">{m.label}</div>
          </div>
        ))}
      </div>

      {route.recommendation_reason && (
        <p className="text-xs text-blue-300/80 bg-blue-950/20 border border-blue-800/30 rounded-lg px-3 py-2 mb-3">
          💡 {route.recommendation_reason}
        </p>
      )}

      {!accepted && (
        <button
          onClick={() => onAccept(route.id)}
          className={`w-full py-2 rounded-lg text-sm font-medium transition-colors ${
            route.is_recommended
              ? "bg-blue-600 hover:bg-blue-500 text-white"
              : "bg-slate-700 hover:bg-slate-600 text-slate-300"
          }`}
        >
          Accept Route {route.id}
        </button>
      )}
    </div>
  );
}

// ── Before/After Comparison ────────────────────────────────────────────────────

function ComparisonTable({ comparison }: { comparison: OptimizeResponse["comparison"] }) {
  const dn = comparison.do_nothing as Record<string, unknown>;
  const rec = comparison.recommended as Record<string, unknown>;

  const rows = [
    { label: "Delay", dn: `${dn.delay_hours}h`, rec: `${rec.delay_hours}h` },
    { label: "Extra Cost", dn: "₹0", rec: formatINR(Number(rec.extra_cost_inr || 0)) },
    { label: "Risk Score", dn: `${dn.risk_score}%`, rec: `${rec.risk_score}%` },
    {
      label: "Revenue Impact",
      dn: dn.revenue_lost_inr ? `-${formatINR(Number(dn.revenue_lost_inr))}` : "-",
      rec: rec.revenue_saved_inr ? `+${formatINR(Number(rec.revenue_saved_inr))} saved` : "-",
    },
  ];

  return (
    <div className="bg-navy-800 border border-slate-700 rounded-xl overflow-hidden mb-6">
      <div className="px-5 py-3 border-b border-slate-700">
        <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Before vs. After</h3>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs text-slate-500 border-b border-slate-700">
            <th className="text-left px-5 py-2">Metric</th>
            <th className="text-left px-5 py-2 text-red-400">Do Nothing</th>
            <th className="text-left px-5 py-2 text-green-400">Recommended</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.label} className="border-b border-slate-700/40">
              <td className="px-5 py-2 text-slate-400">{r.label}</td>
              <td className="px-5 py-2 text-red-300 font-medium">{r.dn}</td>
              <td className="px-5 py-2 text-green-300 font-medium">{r.rec}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Reroute Page ───────────────────────────────────────────────────────────────

export default function ReroutePage() {
  const { shipmentId } = useParams<{ shipmentId: string }>();
  const router = useRouter();

  const [shipment, setShipment] = useState<Shipment | null>(null);
  const [result, setResult] = useState<OptimizeResponse | null>(null);
  const [weights, setWeights] = useState<Weights>({ cost: 0.25, time: 0.35, carbon: 0.15, risk: 0.25 });
  const [loading, setLoading] = useState(true);
  const [optimizing, setOptimizing] = useState(false);
  const [acceptedId, setAcceptedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!shipmentId) return;
    api.shipment(shipmentId).then((s) => {
      setShipment(s);
      return api.optimizeRoutes({ shipment_id: shipmentId, weights });
    })
    .then(setResult)
    .catch((e) => setError(e.message))
    .finally(() => setLoading(false));
  }, [shipmentId]);

  const reoptimize = () => {
    setOptimizing(true);
    api.optimizeRoutes({ shipment_id: shipmentId!, weights })
      .then(setResult)
      .catch(() => {})
      .finally(() => setOptimizing(false));
  };

  const handleAccept = async (routeId: string) => {
    await api.acceptRoute(shipmentId!, routeId);
    setAcceptedId(routeId);
    // Trigger rescore so dashboard picks up the change
    await api.rescoreShipments().catch(() => {});
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96 text-slate-400">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className="flex items-center justify-center h-96 text-slate-400">
        <div className="text-center space-y-2">
          <div className="text-red-400 font-semibold">Failed to load routes</div>
          <p className="text-sm">{error}</p>
          <button onClick={() => router.back()} className="text-blue-400 text-sm underline">← Back</button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-2">
        <button onClick={() => router.back()} className="text-slate-500 hover:text-white text-sm">← Back</button>
        <span className="text-slate-600">/</span>
        <span className="text-sm text-slate-400">Route Optimization</span>
      </div>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">
            Reroute
            <span className="ml-2 text-blue-400 font-mono">{shipmentId}</span>
          </h1>
          {shipment && (
            <p className="text-slate-400 text-sm mt-1">
              {shipment.origin.city} → {shipment.destination.city} · {shipment.carrier} · {formatINR(shipment.revenue)} revenue
            </p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: sliders */}
        <div className="lg:col-span-1">
          <WeightSliders weights={weights} onChange={setWeights} />
          <button
            onClick={reoptimize}
            disabled={optimizing}
            className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
          >
            {optimizing ? "Optimizing…" : "Re-optimize"}
          </button>
        </div>

        {/* Right: comparison + routes */}
        <div className="lg:col-span-2 space-y-4">
          <ComparisonTable comparison={result.comparison} />
          {result.alternatives.map((r) => (
            <RouteCard
              key={r.id}
              route={r}
              onAccept={handleAccept}
              accepted={acceptedId === r.id}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
