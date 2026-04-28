import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "SupplySense AI — Supply Chain Resilience",
  description: "Real-time supply chain disruption detection and dynamic rerouting",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-navy-900 text-slate-100 min-h-screen">
        <Navbar />
        <main className="pt-16">{children}</main>
      </body>
    </html>
  );
}
