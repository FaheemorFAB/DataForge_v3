"use client";

import React from "react";
import Link from "next/link";
import Logo from "../Logo";
import { CheckCircle2, ShieldCheck, Zap } from "lucide-react";

export default function Footer() {
  const handleNavClick = (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
    if (href.includes("#")) {
      const hash = href.split("#")[1];
      if (typeof window !== "undefined") {
        if (window.location.pathname === "/" || window.location.pathname === "") {
          e.preventDefault();
          const element = document.getElementById(hash);
          if (element) {
            (window as any).__isProgrammaticScrolling = true;
            const headerOffset = 72;
            const targetY = element.getBoundingClientRect().top + window.pageYOffset - headerOffset;

            window.scrollTo({
              top: Math.max(0, targetY),
              behavior: "smooth",
            });
            window.history.pushState(null, "", `/#${hash}`);

            setTimeout(() => {
              (window as any).__isProgrammaticScrolling = false;
            }, 850);
          } else {
            window.location.hash = hash;
          }
        }
      }
    }
  };

  return (
    <footer className="px-5 md:px-8 pt-16 pb-10 border-t mt-auto w-full transition-colors duration-300" style={{ borderColor: "var(--border)", background: "var(--bg)" }}>
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col lg:flex-row justify-between items-start gap-10 lg:gap-16 mb-12">
          {/* Brand Info */}
          <div className="flex flex-col gap-4 text-left max-w-sm">
            <div className="flex items-center gap-3">
              <Logo size={28} textSize={19} />
            </div>
            <p className="text-xs leading-relaxed" style={{ color: "var(--txt-m)" }}>
              High-throughput data engineering and automated machine learning. From raw files and databases to production-ready models in seconds.
            </p>
          </div>

          {/* Grouped Link Columns */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-10 sm:gap-14 md:gap-16">
            {/* Product Links */}
            <div className="flex flex-col gap-3 text-left">
              <h4 className="text-[10px] font-mono font-bold uppercase tracking-widest" style={{ color: "var(--txt-f)" }}>Product</h4>
              <ul className="flex flex-col gap-2 text-xs" style={{ color: "var(--txt-m)" }}>
                <li><Link href="/#pipeline" onClick={(e) => handleNavClick(e, "/#pipeline")} className="cursor-pointer hover:text-[color:var(--txt)] transition-colors">Auto Pipeline</Link></li>
                <li><Link href="/#pipeline" onClick={(e) => handleNavClick(e, "/#pipeline")} className="cursor-pointer hover:text-[color:var(--txt)] transition-colors">Interactive Demo</Link></li>
                <li><Link href="/docs" className="cursor-pointer hover:text-[color:var(--txt)] transition-colors">Documentation</Link></li>
                <li><Link href="/workspace" className="cursor-pointer hover:text-[color:var(--txt)] transition-colors">Launch Workspace</Link></li>
                <li><Link href="/pricing" className="cursor-pointer hover:text-[color:var(--txt)] transition-colors">Pricing</Link></li>
              </ul>
            </div>

            {/* Solutions Links */}
            <div className="flex flex-col gap-3 text-left">
              <h4 className="text-[10px] font-mono font-bold uppercase tracking-widest" style={{ color: "var(--txt-f)" }}>Solutions</h4>
              <ul className="flex flex-col gap-2 text-xs" style={{ color: "var(--txt-m)" }}>
                <li><Link href="/#audiences" onClick={(e) => handleNavClick(e, "/#audiences")} className="cursor-pointer hover:text-[color:var(--txt)] transition-colors">Who Uses It</Link></li>
                <li><Link href="/#audiences" onClick={(e) => handleNavClick(e, "/#audiences")} className="cursor-pointer hover:text-[color:var(--txt)] transition-colors">Target Personas</Link></li>
              </ul>
            </div>

            {/* Company Links */}
            <div className="flex flex-col gap-3 text-left">
              <h4 className="text-[10px] font-mono font-bold uppercase tracking-widest" style={{ color: "var(--txt-f)" }}>Company</h4>
              <ul className="flex flex-col gap-2 text-xs" style={{ color: "var(--txt-m)" }}>
                <li><Link href="/#about" onClick={(e) => handleNavClick(e, "/#about")} className="cursor-pointer hover:text-[color:var(--txt)] transition-colors">About</Link></li>
                <li><Link href="/#team" onClick={(e) => handleNavClick(e, "/#team")} className="cursor-pointer hover:text-[color:var(--txt)] transition-colors">DataForge Builders</Link></li>
              </ul>
            </div>
          </div>
        </div>

        {/* Footer Bottom */}
        <div className="pt-8 border-t flex flex-col sm:flex-row justify-center items-center gap-4" style={{ borderColor: "var(--border)" }}>
          <span className="text-[10px] font-mono tracking-wider uppercase" style={{ color: "var(--txt-m)" }}>
            © 2026 DATAFORGE PLATFORM · ALL RIGHTS RESERVED
          </span>
        </div>
      </div>
    </footer>
  );
}
