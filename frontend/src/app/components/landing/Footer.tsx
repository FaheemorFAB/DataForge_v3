import React from "react";
import Logo from "../Logo";

export default function Footer() {
  return (
    <footer className="px-5 md:px-8 pt-16 pb-8 border-t mt-auto" style={{ borderColor: "var(--border)", background: "var(--bg)" }}>
      <div className="max-w-6xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 mb-12">
          {/* Brand Info */}
          <div className="md:col-span-5 flex flex-col gap-4">
            <div className="flex items-center">
              <Logo size={32} textSize={20} />
            </div>
            <p className="text-xs leading-relaxed max-w-sm" style={{ color: "var(--txt-m)" }}>
              An automated analytics platform that takes raw datasets from upload to insight, without the setup.
            </p>
            <p className="text-[11px]" style={{ color: "var(--txt-m)" }}>
              Built with ❤️ by DataForge Team.
            </p>
          </div>

          {/* Product Links */}
          <div className="md:col-span-2 flex flex-col gap-3">
            <h4 className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-f)" }}>Product</h4>
            <ul className="flex flex-col gap-2 text-xs" style={{ color: "var(--txt-m)" }}>
              <li className="cursor-pointer hover:text-[color:var(--txt)] transition-colors">Ingestion</li>
              <li className="cursor-pointer hover:text-[color:var(--txt)] transition-colors">Cleaning</li>
              <li className="cursor-pointer hover:text-[color:var(--txt)] transition-colors">AutoML</li>
              <li className="cursor-pointer hover:text-[color:var(--txt)] transition-colors">Reports</li>
            </ul>
          </div>

          {/* Resources Links */}
          <div className="md:col-span-2 flex flex-col gap-3">
            <h4 className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-f)" }}>Resources</h4>
            <ul className="flex flex-col gap-2 text-xs" style={{ color: "var(--txt-m)" }}>
              <li className="cursor-pointer hover:text-[color:var(--txt)] transition-colors">Documentation</li>
              <li className="cursor-pointer hover:text-[color:var(--txt)] transition-colors">Changelog</li>
              <li className="cursor-pointer hover:text-[color:var(--txt)] transition-colors">Status</li>
            </ul>
          </div>

          {/* Team Links */}
          <div className="md:col-span-3 flex flex-col gap-3">
            <h4 className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-f)" }}>Team</h4>
            <ul className="flex flex-col gap-2 text-xs" style={{ color: "var(--txt-m)" }}>
              <li className="cursor-pointer hover:text-[color:var(--txt)] transition-colors">GCET, Ganderbal</li>
              <li className="cursor-pointer hover:text-[color:var(--txt)] transition-colors">Contact</li>
            </ul>
          </div>
        </div>

        {/* Footer Bottom */}
        <div className="pt-8 border-t flex flex-col sm:flex-row justify-between items-center gap-4" style={{ borderColor: "var(--border)" }}>
          <span className="text-[10px] font-mono tracking-wider uppercase" style={{ color: "var(--txt-m)" }}>
            © 2026 DATAFORGE
          </span>
          <span className="text-[10px] font-mono tracking-wider uppercase" style={{ color: "var(--txt-m)" }}>
            PRIVACY FIRST · OAUTH-SECURED UPLOADS
          </span>
        </div>
      </div>
    </footer>
  );
}
