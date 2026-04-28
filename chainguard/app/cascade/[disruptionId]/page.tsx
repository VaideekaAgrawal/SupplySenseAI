"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, CascadeResult, CascadeNode } from "@/lib/api";
import { formatINR } from "@/lib/utils";
import Link from "next/link";

// ── Cascade Tree Node (recursive) ─────────────────────────────────────────────

function TreeNode({ node, depth = 0 }: { node: CascadeNode; depth?: number }) {
  const [expanded, setExpanded] = useState(depth < 2);
  const impact = Math.round(node.impact_score * 100);
  const impactColor =
    impact >= 75 ? "text-red-400 border-red-700"
    : impact >= 50 ? "text-amber-400 border-amber-700"
    : impact >= 25 ? "text-yellow-300 border-yellow-700"
    : "text-green-400 border-green-700";

  const typeIcon: Record<string, string> = {
    source: "🔴",
    shipment: "📦",
    warehouse: "🏭",
    retailer: "🏪",
  };

  return (
    <div className={`${depth > 0 ? "ml-6 border-l border-slate-700 pl-4" : ""}`}>
      <div
        className={`flex items-start gap-3 py-2 cursor-pointer group`}
        onClick={() => node.children.length > 0 && setExpanded(!expanded)}
      >
        <div className="mt-0.5 text-base">{typeIcon[node.node_type] || "📍"}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-white">{node.name}</span>
            <span className={`text-xs px-1.5 py-0.5 rounded border bg-opacity-20 ${impactColor}`}>
              {impact}% impact
            </span>
            {depth === 0 && (
              <span className="text-xs bg-red-900/40 text-red-300 border border-red-700 px-1.5 py-0.5 rounded">SOURCE</span>
            )}
          </div>
          <div className="flex gap-4 mt-1 text-xs text-slate-400">
            <span>+{node.delay_hours}h delay</span>
            {node.revenue_at_risk > 0 && <span className="text-amber-400">{formatINR(node.revenue_at_risk)} at risk</span>}
            {node.customers_affected > 0 && <span>{node.customers_affected.toLocaleString()} customers</span>}
          </div>
          {node.risk_factors[0] && (
            <div className="mt-1 text-xs text-slate-500 italic">{node.risk_factors[0].detail}</div>
          )}
        </div>
        {node.children.length > 0 && (
          <span className="text-slate-500 text-xs mt-1">{expanded ? "▼" : "▶"} {node.children.length}</span>
        )}
      </div>

      {expanded && node.children.map((child) => (
        <TreeNode key={child.node_id} node={child} depth={depth + 1} />
      ))}
    </div>
  );
}

// ── Summary Bar ───────────────────────────────────────────────────────────────

function SummaryBar({ summary }: { summary: CascadeResult["summary"] }) {
  const stats = [
    { label: "Shipments Hit", value: summary.total_shipments, color: "text-red-400" },
    { label: "Retailers Affected", value: summary.total_retailers, color: "text-amber-400" },
    { label: "Revenue at Risk", value: formatINR(summary.revenue_at_risk), color: "text-red-300" },
    { label: "Customers Affected", value: summary.customers_affected.toLocaleString(), color: "text-orange-300" },
    { label: "Max Delay", value: `${summary.max_delay_hours}h`, color: "text-yellow-300" },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-6">
      {stats.map((s) => (
        <div key={s.label} className="bg-red-950/20 border border-red-800/40 rounded-xl p-4 text-center">
          <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
          <div className="text-xs text-slate-400 mt-1">{s.label}</div>
        </div>
      ))}
    </div>
  );
}

// ── Cascade Page ───────────────────────────────────────────────────────────────

export default function CascadePage() {
  const { disruptionId } = useParams<{ disruptionId: string }>();
  const router = useRouter();
  const [data, setData] = useState<CascadeResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!disruptionId) return;
    api.cascade(disruptionId)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [disruptionId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96 text-slate-400">
        <div className="text-center space-y-3">
          <div className="w-8 h-8 border-2 border-red-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p>Propagating disruption cascade…</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex items-center justify-center h-96 text-slate-400">
        <div className="text-center space-y-2">
          <div className="text-red-400 font-semibold">Failed to load cascade</div>
          <p className="text-sm">{error}</p>
          <button onClick={() => router.back()} className="text-blue-400 text-sm underline">← Back</button>
        </div>
      </div>
    );
  }

  const affectedShipmentIds = data.affected
    .filter((n) => n.node_type === "shipment")
    .map((n) => n.node_id)
    .slice(0, 5);

  return (
    <div className="max-w-5xl mx-auto px-6 py-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-2">
        <button onClick={() => router.back()} className="text-slate-500 hover:text-white text-sm">← Back</button>
        <span className="text-slate-600">/</span>
        <span className="text-sm text-slate-400">Cascade Analysis</span>
      </div>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">
            Cascade Propagation
            <span className="ml-2 text-red-400 text-base font-mono">{data.disruption_id}</span>
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            {data.time_horizon_hours}h time horizon · Source: {data.source.name}
          </p>
        </div>
        <div className="flex gap-2">
          <Link href="/reroute"
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg font-medium transition-colors">
            Reroute Affected →
          </Link>
        </div>
      </div>

      {/* Summary */}
      <SummaryBar summary={data.summary} />

      {/* Cascade Tree */}
      <div className="bg-navy-800 border border-slate-700 rounded-xl p-6 mb-6">
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">
          Propagation Tree
        </h2>
        <TreeNode node={data.source} depth={0} />
      </div>

      {/* AI recommendation prompt */}
      <div className="bg-blue-950/30 border border-blue-800/40 rounded-xl p-4 flex items-center justify-between">
        <div>
          <div className="text-blue-300 font-medium">Get AI Mitigation Plan</div>
          <div className="text-slate-400 text-sm mt-0.5">Ask SupplySense AI for specific rerouting and supplier actions</div>
        </div>
        <Link href={`/chat?q=What+should+I+do+about+${data.disruption_id}?`}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg font-medium">
          Ask AI →
        </Link>
      </div>
    </div>
  );
}
