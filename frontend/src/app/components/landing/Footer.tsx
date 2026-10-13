import React from "react";
import Link from "next/link";
import Logo from "../Logo";
import { CheckCircle2, ShieldCheck, Zap } from "lucide-react";

export default function Footer() {
  return (
    <footer className="px-5 md:px-8 pt-16 pb-10 border-t mt-auto w-full transition-colors duration-300" style={{ borderColor: "var(--border)", background: "var(--bg)" }}>
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 mb-12">
          
          {/* Brand Info */}
          <div className="md:col-span-5 flex flex-col gap-4 text-left">
            <div className="flex items-center gap-3">
              <Logo size={28} textSize={19} />
              <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-mono border"
                style={{
                  background: "rgba(16, 185, 129, 0.08)",
                  borderColor: "rgba(16, 185, 129, 0.25)",
                  color: "#10b981",
                }}>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>Operational</span>
              </div>
            </div>
            <p className="text-xs leading-relaxed max-w-sm" style={{ color: "var(--txt-m)" }}>
              High-throughput data engineering and automated machine learning. From raw files and databases to production-ready models in seconds.
            </p>
            <div className="flex items-center gap-3 text-[11px] font-mono" style={{ color: "var(--txt-m)" }}>
              <span className="flex items-center gap-1">
                <ShieldCheck size={12} className="text-emerald-400" /> OAuth & JWT Secured
              </span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <Zap size={12} className="text-orange-400" /> FLAML & Gemini 2.5
              </span>
            </div>
          </div>

          {/* Product Links */}
          <div className="md:col-span-2 flex flex-col gap-3 text-left">
            <h4 className="text-[10px] font-mono font-bold uppercase tracking-widest" style={{ color: "var(--txt-f)" }}>Product</h4>
            <ul className="flex flex-col gap-2 text-xs" style={{ color: "var(--txt-m)" }}>
              <li><Link href="/#pipeline" className="cursor-pointer hover:text-[color:var(--txt)] transition-colors">Auto Pipeline</Link></li>
              <li><Link href="/#audiences" className="cursor-pointer hover:text-[color:var(--txt)] transition-colors">Who Uses It</Link></li>
              <li><Link href="/#platform-architecture" className="cursor-pointer hover:text-[color:var(--txt)] transition-colors">Architecture</Link></li>
              <li><Link href="/#origin" className="cursor-pointer hover:text-[color:var(--txt)] transition-colors">Our Origin</Link></li>
            </ul>
          </div>

          {/* Resources Links */}
          <div className="md:col-span-2 flex flex-col gap-3 text-left">
            <h4 className="text-[10px] font-mono font-bold uppercase tracking-widest" style={{ color: "var(--txt-f)" }}>Workspace</h4>
            <ul className="flex flex-col gap-2 text-xs" style={{ color: "var(--txt-m)" }}>
              <li><Link href="/workspace" className="cursor-pointer hover:text-[color:var(--txt)] transition-colors">Launch Workspace</Link></li>
              <li><Link href="/#audiences" className="cursor-pointer hover:text-[color:var(--txt)] transition-colors">Target Personas</Link></li>
              <li><Link href="/#pipeline" className="cursor-pointer hover:text-[color:var(--txt)] transition-colors">Interactive Demo</Link></li>
            </ul>
          </div>

          {/* Team Links */}
          <div className="md:col-span-3 flex flex-col gap-3 text-left">
            <h4 className="text-[10px] font-mono font-bold uppercase tracking-widest" style={{ color: "var(--txt-f)" }}>Engineers</h4>
            <ul className="flex flex-col gap-2 text-xs" style={{ color: "var(--txt-m)" }}>
              <li><Link href="/#meet-the-builders" className="cursor-pointer hover:text-[color:var(--txt)] transition-colors">DataForge Builders</Link></li>
              <li><span className="text-[11px] opacity-60">FastAPI · PyTorch · Scikit-Learn · Next.js</span></li>
            </ul>
          </div>
        </div>

        {/* Footer Bottom */}
        <div className="pt-8 border-t flex flex-col sm:flex-row justify-between items-center gap-4" style={{ borderColor: "var(--border)" }}>
          <span className="text-[10px] font-mono tracking-wider uppercase" style={{ color: "var(--txt-m)" }}>
            © 2026 DATAFORGE PLATFORM · ALL RIGHTS RESERVED
          </span>
          <span className="text-[10px] font-mono tracking-wider uppercase" style={{ color: "var(--txt-m)" }}>
            AUTONOMOUS DATA ARCHITECTURE
          </span>
        </div>
      </div>
    </footer>
  );
}
