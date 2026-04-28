"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, Disruption } from "@/lib/api";

export default function CascadeIndexPage() {
  const [disruptions, setDisruptions] = useState<Disruption[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.disruptions().then(setDisruptions).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="flex items-center justify-center h-64 text-slate-400">Loading disruptions…</div>
  );

  return (
    <div className="max-w-3xl mx-auto px-6 py-6">
      <h1 className="text-2xl font-bold text-white mb-2">Cascade Analysis</h1>
      <p className="text-slate-400 text-sm mb-6">Select a disruption to view its supply chain propagation tree.</p>
      <div className="space-y-3">
        {disruptions.map((d) => (
          <Link key={d.id} href={`/cascade/${d.id}`}
            className="block bg-navy-800 border border-slate-700 hover:border-red-600 rounded-xl p-5 transition-colors">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-semibold text-white">{d.title}</div>
                <div className="text-sm text-slate-400 mt-0.5">{d.location.city} · {d.type} · {d.status}</div>
              </div>
              <div className="text-right">
                <div className="text-red-400 font-bold">{Math.round(d.severity * 100)}%</div>
                <div className="text-xs text-slate-500">severity</div>
              </div>
            </div>
            {d.cascade && (
              <div className="mt-3 text-xs text-slate-500 flex gap-4">
                <span>{d.cascade.total_shipments} shipments</span>
                <span>{d.cascade.customers_affected.toLocaleString()} customers</span>
                <span className="text-amber-400">₹{(d.cascade.revenue_at_risk / 100000).toFixed(2)}L at risk</span>
              </div>
            )}
          </Link>
        ))}
        {disruptions.length === 0 && (
          <div className="text-slate-400 text-center py-8">No active disruptions. The network is stable.</div>
        )}
      </div>
    </div>
  );
}
