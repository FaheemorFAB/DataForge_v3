"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Check,
  ShieldCheck,
  ArrowRight,
  ArrowLeft,
  Lock,
  Sparkles,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface PlanConfig {
  id: string;
  name: string;
  priceMonthly: number;
  rowLimit: string;
  description: string;
  features: string[];
  dodoProductId?: string;
}

const PLANS: Record<string, PlanConfig> = {
  pro: {
    id: "pro",
    name: "Pro Analyst",
    priceMonthly: 29,
    rowLimit: "Up to 250,000 Rows • 5 GB Storage",
    description: "For solo data analysts & practitioners requiring advanced exports, EDA slides & AutoML Docker containers.",
    dodoProductId: "pdt_0Nq982Kd8DHmCrFIX4XC2",
    features: [
      "Unlimited Data Ingestion (no file count caps)",
      "250,000 rows in-memory DuckDB processing (10x Free)",
      "Cloud Storage: 5 GB workspace storage (20x Free)",
      "Data Ingestion: Local CSV/Excel, Google Sheets & OneDrive/M365",
      "Full File Downloads: CSV, Excel (.xlsx), Parquet & JSON",
      "Executive EDA presentation slides export (PPTX & PDF)",
      "AutoML production Docker containers & deployment files",
      "Pipeline Code Export: Standalone Python & dbt models",
      "50 AutoML tournaments / month",
      "250 AI natural-language queries / month",
      "Priority email support",
    ],
  },
  team: {
    id: "team",
    name: "Team Collaboration",
    priceMonthly: 79,
    rowLimit: "Up to 1,000,000 Rows • 25 GB Storage",
    description: "For analytics teams requiring shared datasets, multi-role collaboration, and shared database vaults.",
    dodoProductId: "pdt_0Nq98DJ0O2SJ5pqxJeFHz",
    features: [
      "Multi-user team collaboration with 3 roles: Viewer, Analyst, Admin",
      "Up to 5 team member seats with role permissions",
      "Shared Database Connection Vault (PostgreSQL, MySQL, SQLite, DuckDB)",
      "1,000,000 rows processing with out-of-core streaming",
      "25 GB shared organization storage",
      "Unlimited Team Data Ingestion & Pipeline Uploads",
      "Apache Airflow production DAG exports & pipeline code",
      "Direct Database Push & Cross-team exports",
      "200 AutoML tournaments / month & Model Registry REST API",
      "1,000 AI natural-language queries / month",
      "Immutable governance audit logs & compliance trail",
    ],
  },
};

function BillingCheckoutContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const rawPlan = searchParams.get("plan")?.toLowerCase();
  const activePlanKey = rawPlan && rawPlan in PLANS ? rawPlan : "team";

  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const { user } = useAuth();
  const plan = PLANS[activePlanKey] || PLANS.team;
  const currentPrice = plan.priceMonthly;

  useEffect(() => {
    const status = searchParams.get("status");
    const paymentId = searchParams.get("payment_id");
    if (status === "succeeded" || status === "success" || paymentId) {
      setSuccessMsg(`✓ Payment confirmed! Upgraded your workspace to ${plan.name}. Redirecting to workspace...`);
      apiFetch("/subscription/upgrade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          plan: activePlanKey,
          direct_apply: true,
        }),
      }).catch(() => {});
      const timer = setTimeout(() => {
        router.push("/workspace");
      }, 2000);
      return () => clearTimeout(timer);
    } else if (status === "failed") {
      setErrorMsg("Payment was unsuccessful or cancelled. Please try again.");
    }
  }, [searchParams, activePlanKey, plan.name, router]);

  const handleActivatePlan = async () => {
    setIsLoading(true);
    setErrorMsg("");
    setSuccessMsg("");

    try {
      const res = await apiFetch("/subscription/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          plan: activePlanKey,
          direct_apply: false,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || data.error || "Unable to initiate payment checkout.");
      }

      const data = await res.json();
      if (data.checkout_url) {
        setSuccessMsg("✓ Redirecting to Dodo Payments secure checkout...");
        window.location.href = data.checkout_url;
        return;
      }

      setSuccessMsg(`✓ Successfully activated ${plan.name}! All limits and features unlocked.`);
      setTimeout(() => {
        router.push("/workspace");
      }, 1000);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to initiate payment.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen py-10 px-4 sm:px-6 lg:px-8 flex flex-col justify-between"
      style={{ background: "var(--bg)", color: "var(--txt)" }}
    >
      <div className="max-w-xl mx-auto w-full">
        {/* Navigation / Back */}
        <div className="flex items-center justify-between mb-6">
          <Link
            href="/pricing"
            className="flex items-center gap-1.5 text-xs font-bold transition-opacity hover:opacity-80"
            style={{ color: "var(--txt-m)" }}
          >
            <ArrowLeft size={14} />
            <span>Change Plan / Back to Pricing</span>
          </Link>
        </div>

        {/* Minimalist Order Summary Card */}
        <div
          className="p-6 sm:p-8 rounded-2xl border shadow-2xl space-y-6"
          style={{ background: "var(--card)", borderColor: "var(--border)" }}
        >
          {/* Header & Pricing */}
          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 border-b pb-5" style={{ borderColor: "var(--border)" }}>
            <div>
              <span className="text-[11px] font-mono uppercase font-bold text-indigo-400 tracking-wider">
                Subscription Checkout
              </span>
              <h2 className="text-2xl sm:text-3xl font-black mt-1" style={{ color: "var(--txt)" }}>
                {plan.name}
              </h2>
              <p className="text-xs mt-1 max-w-sm" style={{ color: "var(--txt-m)" }}>
                {plan.description}
              </p>
            </div>

            <div className="sm:text-right">
              <div className="text-3xl font-black font-mono" style={{ color: "var(--txt)" }}>
                ${currentPrice}
                <span className="text-sm font-bold text-indigo-400 ml-1">
                  /month
                </span>
              </div>
              <span className="text-[11px] font-mono text-emerald-400 font-bold block mt-0.5">
                Billed Monthly · Cancel Anytime
              </span>
            </div>
          </div>

          {/* Capacity Pill */}
          <div
            className="flex items-center justify-between px-3.5 py-2 rounded-xl border text-xs"
            style={{ background: "var(--surface)", borderColor: "var(--border)" }}
          >
            <span className="font-mono text-[11px] text-[var(--txt-m)] uppercase font-semibold">Capacity</span>
            <span className="font-bold text-indigo-300 font-mono text-xs">{plan.rowLimit}</span>
          </div>

          {/* Included Capabilities */}
          <div className="space-y-3">
            <div className="flex items-center gap-1.5 text-xs font-bold text-indigo-400">
              <Sparkles size={13} className="shrink-0" />
              <span>Included Capabilities & Entitlements:</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {plan.features.map((feat, i) => (
                <div key={i} className="flex items-start gap-2 text-xs">
                  <div className="w-4 h-4 rounded-full bg-emerald-500/15 text-emerald-400 flex items-center justify-center shrink-0 mt-0.5">
                    <Check size={11} strokeWidth={3} />
                  </div>
                  <span style={{ color: "var(--txt)" }}>{feat}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Feedback Alerts */}
          {errorMsg && (
            <div className="p-3.5 rounded-xl border bg-rose-500/10 border-rose-500/20 text-rose-400 text-xs font-mono">
              ⚠ {errorMsg}
            </div>
          )}

          {successMsg && (
            <div className="p-3.5 rounded-xl border bg-emerald-500/10 border-emerald-500/20 text-emerald-400 text-xs font-mono">
              {successMsg}
            </div>
          )}

          {/* Checkout Action Button */}
          <div className="space-y-3 pt-2">
            <button
              onClick={handleActivatePlan}
              disabled={isLoading}
              className="w-full py-3.5 px-6 rounded-xl font-bold text-sm flex items-center justify-center gap-2 transition-all hover:scale-[1.01] active:scale-[0.99] cursor-pointer shadow-xl"
              style={{
                background: "var(--accent)",
                color: "#ffffff",
                boxShadow: "0 4px 16px var(--glow)",
              }}
            >
              <Lock size={15} />
              <span>{isLoading ? "Connecting to Dodo Payments..." : `Proceed to Checkout ($${currentPrice}/month)`}</span>
              <ArrowRight size={15} />
            </button>

            <div className="flex items-center justify-center gap-1.5 pt-1 text-center">
              <ShieldCheck size={13} className="text-emerald-400" />
              <span className="text-[11px] font-mono text-[var(--txt-m)]">
                Secure 256-bit encrypted checkout via Dodo Payments
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Minimal Footer */}
      <footer className="mt-12 text-center text-xs" style={{ color: "var(--txt-m)" }}>
        <p>DataForge Inc. · Powered by Dodo Payments</p>
      </footer>
    </div>
  );
}

export default function BillingCheckoutPage() {
  return (
    <React.Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center font-mono text-xs" style={{ background: "var(--bg)", color: "var(--txt-m)" }}>
          Loading checkout session...
        </div>
      }
    >
      <BillingCheckoutContent />
    </React.Suspense>
  );
}
