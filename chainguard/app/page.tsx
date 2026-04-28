"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();

  // Auto-redirect to dashboard for demo mode
  useEffect(() => {
    router.replace("/dashboard");
  }, [router]);

  return (
    <div className="min-h-screen bg-navy-900 flex items-center justify-center">
      <div className="text-center space-y-6">
        <div className="flex items-center justify-center gap-3 mb-2">
          <span className="text-4xl">⛓️</span>
          <h1 className="text-4xl font-bold text-white">SupplySense AI</h1>
        </div>
        <p className="text-slate-400 text-lg">Smart Supply Chain Resilience Platform</p>
        <div className="animate-pulse text-slate-500 text-sm">Loading dashboard…</div>
      </div>
    </div>
  );
}
