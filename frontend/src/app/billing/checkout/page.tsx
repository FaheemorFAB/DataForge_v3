"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Check,
  ShieldCheck,
  Zap,
  ArrowRight,
  ArrowLeft,
  CreditCard,
  Lock,
  Sparkles,
  Layers,
  Database,
  Users,
  Code,
  HelpCircle,
  ExternalLink,
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
      "Unlimited Data Ingestion (no file count or monthly ingest caps)",
      "250,000 rows in-memory DuckDB processing (10x Free)",
      "Cloud Storage: 5 GB workspace storage (20x Free)",
      "Data Ingestion: Local CSV/Excel, Google Sheets & OneDrive/M365",
      "Full File Downloads: CSV, Excel (.xlsx), Parquet & JSON",
      "Executive EDA presentation slides export (PPTX & PDF)",
      "AutoML production Docker containers & deployment files",
      "Pipeline Code Export: Standalone Python & dbt models",
      "50 AutoML tournaments / month (10x Free)",
      "250 AI natural-language queries / month (10x Free)",
      "Relational Join Studio & multi-table merge",
      "Priority email support",
    ],
  },
  team: {
    id: "team",
    name: "Team Collaboration",
    priceMonthly: 79,
    rowLimit: "Up to 1,000,000 Rows • 25 GB Storage",
    description: "For analytics teams requiring shared datasets, collaboration with 3 roles and database connections.",
    dodoProductId: "pdt_0Nq98DJ0O2SJ5pqxJeFHz",
    features: [
      "Multi-user team collaboration with 3 roles: Viewer, Analyst, Admin",
      "Up to 5 team member seats with role permissions",
      "Shared Database Connection Vault (PostgreSQL, MySQL, SQLite, DuckDB)",
      "1,000,000 rows processing with out-of-core streaming (4x Pro, 40x Free)",
      "25 GB shared organization storage (5x Pro)",
      "Unlimited Team Data Ingestion & Pipeline Uploads",
      "Apache Airflow production DAG exports & pipeline code",
      "Direct Database Push & Cross-team exports",
      "200 AutoML tournaments / month & Model Registry REST API (4x Pro)",
      "1,000 AI natural-language queries / month (4x Pro)",
      "Immutable governance audit logs & compliance trail",
    ],
  },
};

function BillingCheckoutContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialPlan = searchParams.get("plan")?.toLowerCase() || "pro";
  const selectedPlanKey = initialPlan in PLANS ? initialPlan : "pro";

  const [activePlan, setActivePlan] = useState<string>(selectedPlanKey);
  const [isLoading, setIsLoading] = useState(false);
  const [isSandboxActivating, setIsSandboxActivating] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const { user } = useAuth();
  const plan = PLANS[activePlan] || PLANS.pro;
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
          plan: activePlan,
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
  }, [searchParams, activePlan, plan.name, router]);

  const handleActivatePlan = async () => {
    setIsLoading(true);
    setErrorMsg("");
    setSuccessMsg("");

    try {
      const res = await apiFetch("/subscription/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          plan: activePlan,
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

  const handleDevDirectUpgrade = async () => {
    setIsSandboxActivating(true);
    setErrorMsg("");
    try {
      const res = await apiFetch("/subscription/upgrade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          plan: activePlan,
          direct_apply: true,
        }),
      });
      if (res.ok) {
        setSuccessMsg(`✓ Successfully upgraded to ${plan.name}! Redirecting to workspace...`);
        setTimeout(() => {
          router.push("/workspace");
        }, 1200);
      } else {
        const data = await res.json().catch(() => ({}));
        setErrorMsg(data.detail || "Direct upgrade failed.");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Network error");
    } finally {
      setIsSandboxActivating(false);
    }
  };

  return (
    <div
      className="min-h-screen py-12 px-4 sm:px-6 lg:px-8 flex flex-col justify-between"
      style={{ background: "var(--bg)", color: "var(--txt)" }}
    >
      <div className="max-w-4xl mx-auto w-full">
        {/* Navigation / Back */}
        <div className="flex items-center justify-between mb-8">
          <Link
            href="/workspace"
            className="flex items-center gap-1.5 text-xs font-bold transition-opacity hover:opacity-80"
            style={{ color: "var(--txt-m)" }}
          >
            <ArrowLeft size={14} />
            <span>Back to Workspace</span>
          </Link>

          <div className="flex items-center gap-2">
            <span
              className="px-2.5 py-1 rounded-full text-[11px] font-mono font-bold uppercase tracking-wider"
              style={{
                background: "var(--glow)",
                color: "var(--accent)",
                border: "1px solid var(--accent)",
              }}
            >
              Dodo Payments Merchant of Record
            </span>
          </div>
        </div>

        {/* Title & Plan Switcher */}
        <div className="text-center mb-10">
          <h1 className="text-3xl sm:text-4xl font-black tracking-tight" style={{ color: "var(--txt)" }}>
            Upgrade Your DataForge Workspace
          </h1>
          <p className="text-sm mt-2 max-w-lg mx-auto" style={{ color: "var(--txt-m)" }}>
            Unlock out-of-core DuckDB relational queries, Stored Procedure automation, and leak-free AutoML.
          </p>
        </div>

        {/* Main Checkout Card Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
          {/* Plan Selector Sidebar */}
          <div className="space-y-3">
            <label className="text-xs font-mono uppercase tracking-wider font-bold" style={{ color: "var(--txt-m)" }}>
              Select Tier
            </label>

            {Object.values(PLANS).map((p) => {
              const isSelected = activePlan === p.id;
              const price = p.priceMonthly;
              return (
                <div
                  key={p.id}
                  onClick={() => setActivePlan(p.id)}
                  className={`p-4 rounded-2xl border transition-all cursor-pointer ${
                    isSelected
                      ? "border-[var(--accent)] shadow-lg shadow-[var(--accent)]/10"
                      : "hover:border-[var(--txt-m)]/40"
                  }`}
                  style={{
                    background: isSelected ? "var(--surface)" : "var(--card)",
                    borderColor: isSelected ? "var(--accent)" : "var(--border)",
                  }}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-sm" style={{ color: "var(--txt)" }}>
                      {p.name}
                    </span>
                    <span className="text-sm font-black font-mono" style={{ color: "var(--accent)" }}>
                      ${price}/mo
                    </span>
                  </div>
                  <p className="text-[11px] mt-1 line-clamp-2" style={{ color: "var(--txt-m)" }}>
                    {p.rowLimit}
                  </p>
                </div>
              );
            })}

            {/* Merchant Trust Badge */}
            <div
              className="p-4 rounded-2xl border mt-6 space-y-2.5 text-xs"
              style={{ background: "var(--card)", borderColor: "var(--border)" }}
            >
              <div className="flex items-center gap-2 font-bold text-emerald-500">
                <ShieldCheck size={16} />
                <span>Dodo Payments Certified Checkout</span>
              </div>
              <p className="text-[11px]" style={{ color: "var(--txt-m)" }}>
                Payments, sales tax, VAT, and invoices are handled securely by Dodo Payments (Merchant of Record). Cancel anytime with 1-click.
              </p>
              <div className="flex items-center gap-2 pt-1 font-mono text-[10px]" style={{ color: "var(--txt-m)" }}>
                <Lock size={11} />
                <span>256-bit TLS · PCI-DSS Level 1</span>
              </div>
            </div>
          </div>

          {/* Plan Details & Order Summary */}
          <div
            className="md:col-span-2 p-6 sm:p-8 rounded-2xl border shadow-2xl space-y-6"
            style={{ background: "var(--card)", borderColor: "var(--border)" }}
          >
            <div className="flex items-center justify-between border-b pb-5" style={{ borderColor: "var(--border)" }}>
              <div>
                <span className="text-xs font-mono uppercase font-bold text-indigo-400">
                  Order Summary
                </span>
                <h3 className="text-2xl font-black mt-1" style={{ color: "var(--txt)" }}>
                  {plan.name}
                </h3>
                <p className="text-xs mt-0.5" style={{ color: "var(--txt-m)" }}>
                  {plan.description}
                </p>
              </div>

              <div className="text-right">
                <div className="text-3xl font-black font-mono" style={{ color: "var(--txt)" }}>
                  ${currentPrice}
                  <span className="text-xs font-normal ml-1" style={{ color: "var(--txt-m)" }}>
                    one-time
                  </span>
                </div>
                <span className="text-[10px] font-mono text-emerald-500 font-bold">
                  One-Time Payment • Lifetime Access
                </span>
              </div>
            </div>

            {/* Included Features */}
            <div>
              {plan.id === "pro" && (
                <div
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-bold mb-3.5 shadow-sm"
                  style={{
                    background: "var(--surface)",
                    borderColor: "var(--accent)",
                    color: "var(--accent)",
                  }}
                >
                  <Sparkles size={13} className="shrink-0" />
                  <span>Everything in Free Starter, plus:</span>
                </div>
              )}
              {plan.id === "team" && (
                <div
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-bold mb-3.5 shadow-sm"
                  style={{
                    background: "var(--surface)",
                    borderColor: "var(--accent)",
                    color: "var(--accent)",
                  }}
                >
                  <Sparkles size={13} className="shrink-0" />
                  <span>Everything in Pro Analyst, plus:</span>
                </div>
              )}
              <h4 className="text-xs font-mono uppercase font-bold mb-3" style={{ color: "var(--txt-m)" }}>
                Exclusive Capabilities & Entitlements:
              </h4>
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

            {/* Actions */}
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
                <Lock size={16} />
                <span>{isLoading ? "Connecting to Dodo Payments..." : `Pay $${currentPrice} via Dodo Payments (One-Time)`}</span>
                <ArrowRight size={16} />
              </button>

              <div className="flex items-center justify-between pt-1 px-1">
                <span className="text-[11px] font-mono text-emerald-400">
                  ✓ 100% Certified Checkout via Dodo Payments
                </span>
                <button
                  type="button"
                  onClick={handleDevDirectUpgrade}
                  disabled={isSandboxActivating}
                  className="text-[11px] font-mono text-[var(--txt-m)] hover:text-indigo-400 underline cursor-pointer"
                >
                  {isSandboxActivating ? "Activating..." : "Developer Bypass"}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="mt-16 text-center text-xs border-t pt-6" style={{ borderColor: "var(--border)", color: "var(--txt-m)" }}>
        <p>DataForge Inc. · Powered by Dodo Payments (Merchant of Record)</p>
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
