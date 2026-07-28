"use client";

import Link from "next/link";
import { Database } from "lucide-react";

export default function AboutPage() {
  return (
    <div className="min-h-screen relative flex flex-col" style={{ background: "var(--bg)", color: "var(--txt)" }}>
      {/* Navigation */}
      <nav className="px-8 py-6 flex items-center justify-between max-w-7xl mx-auto w-full">
        <Link href="/" className="flex items-center gap-2 group" style={{ textDecoration: 'none' }}>
          <div className="w-8 h-8 rounded-lg flex items-center justify-center transition-transform group-hover:scale-110" style={{ background: "linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%)" }}>
            <Database size={16} className="text-white" />
          </div>
          <span className="font-black text-xl tracking-tight" style={{ background: "linear-gradient(to right, var(--txt), var(--txt-m))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            DataForge
          </span>
        </Link>
        <Link href="/dashboard" className="px-5 py-2.5 rounded-full text-sm font-bold transition-all hover:scale-105 shadow-lg" style={{ background: "var(--accent)", color: "white" }}>
          Go to App
        </Link>
      </nav>

      {/* Main Content */}
      <main className="flex-1 flex items-center justify-center">
        <h1 className="text-4xl md:text-5xl font-black tracking-tight" style={{ color: "var(--txt-m)" }}>
          About Us
        </h1>
      </main>
    </div>
  );
}
