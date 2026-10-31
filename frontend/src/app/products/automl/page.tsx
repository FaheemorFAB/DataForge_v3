"use client";

import React from "react";
import { motion } from "framer-motion";
import Header from "@/app/components/landing/Header";
import Footer from "@/app/components/landing/Footer";
import CTABanner from "@/app/components/landing/CTABanner";
import { BrainCircuit, Activity, BarChart3, Binary } from "lucide-react";

export default function AutoMLPage() {
  const features = [
    {
      icon: <BrainCircuit size={24} style={{ color: "var(--accent)" }} />,
      title: "Zero-Config FLAML",
      description: "Powered by Microsoft's FLAML framework. Automatically selects the best model (XGBoost, LightGBM, Random Forest) for your specific dataset."
    },
    {
      icon: <BarChart3 size={24} style={{ color: "var(--accent)" }} />,
      title: "SHAP Explainability",
      description: "Don't trust a black box. Interactive SHAP value charts explain exactly which features are driving the model's predictions."
    },
    {
      icon: <Activity size={24} style={{ color: "var(--accent)" }} />,
      title: "Real-time Leaderboard",
      description: "Watch models compete in real-time. View metrics like RMSE, R2, and F1-Score as they train."
    },
    {
      icon: <Binary size={24} style={{ color: "var(--accent)" }} />,
      title: "One-Click Export",
      description: "Satisfied with the results? Download the trained .pkl file instantly to deploy it in your own production environment."
    }
  ];

  return (
    <div className="min-h-screen flex flex-col transition-colors duration-300" style={{ background: "var(--bg)", color: "var(--txt)" }}>
      <Header onLoginClick={() => window.location.href = '/login'} />
      
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
                AutoML Studio
              </div>
              <h1 className="font-black mb-6 tracking-tight transition-colors duration-300 leading-[1.1]" style={{ fontSize: "clamp(2rem,5vw,3.8rem)", color: "var(--txt)" }}>
                Train models.<br/>
                <span style={{ color: "var(--accent)" }}>Without writing code.</span>
              </h1>
              <p className="text-sm font-light leading-relaxed transition-colors duration-300 max-w-md" style={{ color: "var(--txt-m)" }}>
                Leverage Microsoft FLAML to automatically test, tune, and select the highest-performing machine learning models for your dataset in seconds.
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
          title="Ready to train your first model?"
          subtitle="Benchmark LightGBM, XGBoost, and Random Forest with automated leaderboard scoring in minutes."
          buttonText="Upload Your Dataset"
          href="/?login=1"
          secondaryButtonText="Executive Reports"
          secondaryHref="/products/reports"
        />
      </div>

      <Footer />
    </div>
  );
}
