"use client";
import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

export interface MapMarker {
  lat: number;
  lng: number;
  label: string;
  color?: string;
  radius?: number;
  popup?: string;
}

export interface MapRoute {
  waypoints: { lat: number; lng: number; name?: string }[];
  color?: string;
  weight?: number;
  dashArray?: string;
  label?: string;
}

interface Props {
  markers?: MapMarker[];
  routes?: MapRoute[];
  center?: [number, number];
  zoom?: number;
  height?: string;
  className?: string;
}

const COLORS = {
  green: "#10b981",
  amber: "#f59e0b",
  red: "#ef4444",
  blue: "#3b82f6",
  cyan: "#06b6d4",
  purple: "#a855f7",
  slate: "#64748b",
};

function resolveColor(c?: string): string {
  return (c && (COLORS as Record<string, string>)[c]) || c || COLORS.blue;
}

export default function MapView({ markers = [], routes = [], center = [22.5, 78.5], zoom = 5, height = "400px", className = "" }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    if (mapRef.current) {
      mapRef.current.remove();
      mapRef.current = null;
    }

    const map = L.map(ref.current, {
      center,
      zoom,
      zoomControl: true,
      attributionControl: false,
    });
    mapRef.current = map;

    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      maxZoom: 18,
    }).addTo(map);

    // markers
    markers.forEach((m) => {
      const col = resolveColor(m.color);
      const r = m.radius || 6;
      const circle = L.circleMarker([m.lat, m.lng], {
        radius: r,
        fillColor: col,
        color: col,
        weight: 2,
        fillOpacity: 0.8,
      }).addTo(map);
      if (m.popup) circle.bindPopup(m.popup);
      else if (m.label) circle.bindPopup(`<b>${m.label}</b>`);
    });

    // routes
    routes.forEach((rt) => {
      if (rt.waypoints.length < 2) return;
      const latlngs = rt.waypoints.map((w) => [w.lat, w.lng] as [number, number]);
      L.polyline(latlngs, {
        color: resolveColor(rt.color),
        weight: rt.weight || 3,
        opacity: 0.8,
        dashArray: rt.dashArray,
      }).addTo(map);
    });

    // fit bounds
    const allPts: [number, number][] = [
      ...markers.map((m) => [m.lat, m.lng] as [number, number]),
      ...routes.flatMap((r) => r.waypoints.map((w) => [w.lat, w.lng] as [number, number])),
    ];
    if (allPts.length >= 2) {
      map.fitBounds(L.latLngBounds(allPts), { padding: [30, 30] });
    }

    return () => {
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(markers), JSON.stringify(routes)]);

  return <div ref={ref} style={{ height, width: "100%" }} className={`rounded-xl overflow-hidden ${className}`} />;
}
