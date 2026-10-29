"use client";

import React from "react";
import { motion } from "framer-motion";
import Header from "@/app/components/landing/Header";
import Footer from "@/app/components/landing/Footer";
import CTABanner from "@/app/components/landing/CTABanner";
import { Database, FileSpreadsheet, ShieldCheck, Zap } from "lucide-react";

export default function IngestionPage() {
  const features = [
    {
      icon: <FileSpreadsheet size={24} style={{ color: "var(--accent)" }} />,
      title: "Universal CSV Support",
      description: "Instantly upload and parse massive CSV datasets with our optimized backend engine. No pre-formatting required."
    },
    {
      icon: <Database size={24} style={{ color: "var(--accent)" }} />,
      title: "Direct Database Connectors",
      description: "Securely link your SQL databases to DataForge for real-time analytics streaming."
    },
    {
      icon: <ShieldCheck size={24} style={{ color: "var(--accent)" }} />,
      title: "OAuth2 Secured",
      description: "Enterprise-grade encryption and authentication ensures your data remains strictly confidential during transfer."
    },
    {
      icon: <Zap size={24} style={{ color: "var(--accent)" }} />,
      title: "Lightning Fast Parsing",
      description: "Powered by Pandas backend processors, DataForge slices through gigabytes of raw data in seconds."
    }
  ];

  return (
    <div className="min-h-screen flex flex-col transition-colors duration-300" style={{ background: "var(--bg)", color: "var(--txt)" }}>
      <Header onLoginClick={() => window.location.href = '/?login=1'} />
      
      <main className="flex-1 max-w-6xl mx-auto w-full px-5 md:px-8 py-20 md:py-32">
        <div className="flex flex-col lg:flex-row gap-16 lg:gap-24 relative">
          
          {/* Left Column - Sticky Hero */}
          <div className="lg:w-1/2 lg:sticky lg:top-32 self-start relative">
            <div className="absolute top-0 left-0 w-64 h-64 rounded-full mix-blend-screen filter blur-[100px] opacity-20 transition-colors duration-500 pointer-events-none" style={{ background: "var(--accent)" }}></div>
            
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="relative z-10"
            >
              <div className="inline-block px-3 py-1 rounded-full border mb-6 text-[10px] font-bold uppercase tracking-widest transition-colors duration-300" style={{ borderColor: "var(--border)", color: "var(--txt-m)", background: "var(--card-bg)" }}>
                Data Ingestion
              </div>
              <h1 className="font-black mb-6 tracking-tight transition-colors duration-300 leading-[1.1]" style={{ fontSize: "clamp(2rem,5vw,3.8rem)", color: "var(--txt)" }}>
                Connect Your Data.<br/>
                <span style={{ color: "var(--accent)" }}>Instantly.</span>
              </h1>
              <p className="text-sm font-light leading-relaxed transition-colors duration-300 max-w-md" style={{ color: "var(--txt-m)" }}>
                Stop wrestling with complex ETL pipelines. DataForge's ingestion engine absorbs your messy data formats seamlessly, securely, and at lightning speed.
              </p>
            </motion.div>
          </div>

          {/* Right Column - Scrollable Features */}
          <div className="lg:w-1/2 flex flex-col gap-6 lg:pt-16">
            {features.map((feat, i) => (
              <motion.div 
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ delay: 0.1 * (i % 3) }}
                className="p-8 md:p-10 rounded-3xl border transition-all duration-300 hover:border-[var(--accent)] hover:shadow-2xl hover:-translate-y-1 group relative overflow-hidden"
                style={{ borderColor: "var(--border)", background: "var(--card-bg)" }}
              >
                <div className="absolute inset-0 opacity-0 group-hover:opacity-5 transition-opacity duration-500" style={{ background: "var(--accent)" }}></div>
                
                <div className="relative z-10 flex flex-col sm:flex-row gap-6">
                  <div className="w-14 h-14 flex-shrink-0 flex items-center justify-center rounded-2xl border transition-colors duration-300 group-hover:border-[var(--accent)] group-hover:bg-[var(--bg)] shadow-sm" style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.02)" }}>
                    {feat.icon}
                  </div>
                  <div>
                    <h3 className="text-sm font-bold mb-1.5 transition-colors duration-300 group-hover:text-[var(--accent)]" style={{ color: "var(--txt)" }}>{feat.title}</h3>
                    <p className="text-xs leading-relaxed transition-colors duration-300" style={{ color: "var(--txt-m)" }}>{feat.description}</p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>

        </div>
      </main>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 mb-16">
        <CTABanner 
          variant="compact"
          title="Ready to start importing?"
          subtitle="Connect CSV, Excel, SQLite, PostgreSQL, and Google Sheets with zero configuration."
          buttonText="Upload Your Dataset"
          href="/?login=1"
          secondaryButtonText="Clean & Transform"
          secondaryHref="/products/cleaning"
        />
      </div>

      <Footer />
    </div>
  );
}
