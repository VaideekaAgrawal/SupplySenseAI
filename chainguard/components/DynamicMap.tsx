import dynamic from "next/dynamic";

export const DynamicMap = dynamic(() => import("./MapView"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-[400px] bg-navy-800 border border-slate-700 rounded-xl flex items-center justify-center text-slate-500">
      Loading map…
    </div>
  ),
});

export type { MapMarker, MapRoute } from "./MapView";
