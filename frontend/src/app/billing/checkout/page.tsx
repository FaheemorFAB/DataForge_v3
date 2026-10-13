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
  priceAnnual: number;
  rowLimit: string;
  description: string;
  features: string[];
  paddlePriceIdMonthly?: string;
  paddlePriceIdAnnual?: string;
}

const PLANS: Record<string, PlanConfig> = {
  pro: {
    id: "pro",
    name: "Pro Analyst",
    priceMonthly: 49,
    priceAnnual: 39,
    rowLimit: "Up to 10,000,000 Rows",
    description: "For senior data analysts, quants, and engineering teams requiring SQL pipelines and AutoML.",
    features: [
      "10,000,000 rows out-of-core DuckDB engine",
      "DuckDB Relational Join Studio (Inner, Left, Outer, Anti)",
      "Automated Stored Procedure Engine (DF-SPE v1)",
      "AutoML Tournament (LightGBM, XGBoost, CatBoost)",
      "Benjamini-Hochberg & BY Multiple-Testing FDR control",
      "Executive Slide Deck & automated business report export",
      "Standalone Python, dbt SQL, and Airflow DAG export",
      "Priority customer and security support",
    ],
  },
  team: {
    id: "team",
    name: "Enterprise Team",
    priceMonthly: 199,
    priceAnnual: 169,
    rowLimit: "Up to 50,000,000 Rows",
    description: "For analytics organizations requiring multi-tenant workspaces, team governance, and model registry.",
    features: [
      "50,000,000 rows distributed and cached in Parquet",
      "Shared organization workspaces & 4-tier RBAC",
      "Centralized Model Registry with Docker microservice deployment",
      "Immutable governance audit logs & compliance trail",
      "Google Sheets-style live collaborator sharing & invitations",
      "Custom Stored Procedure recipes with automated assertion gates",
      "Dedicated Slack / Teams support channel with 1h SLA",
      "SOC2 Type II compliance controls & custom agreements",
    ],
  },
};

function BillingCheckoutContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialPlan = searchParams.get("plan")?.toLowerCase() || "pro";
  const selectedPlanKey = initialPlan in PLANS ? initialPlan : "pro";

  const [activePlan, setActivePlan] = useState<string>(selectedPlanKey);
  const [billingCycle, setBillingCycle] = useState<"monthly" | "annual">("monthly");
  const [isLoading, setIsLoading] = useState(false);
  const [isSandboxActivating, setIsSandboxActivating] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const { user } = useAuth();
  const plan = PLANS[activePlan] || PLANS.pro;
  const currentPrice = billingCycle === "monthly" ? plan.priceMonthly : plan.priceAnnual;

  const handleActivatePlan = async () => {
    setIsLoading(true);
    setErrorMsg("");
    setSuccessMsg("");

    try {
      // Pre-deployment: activate directly with no external payment gateway required
      const res = await apiFetch("/subscription/upgrade", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          plan: activePlan,
          direct_apply: true,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || data.error || "Unable to activate plan.");
      }

      setSuccessMsg(`✓ Successfully activated ${plan.name}! All limits and features unlocked.`);
      setTimeout(() => {
        router.push("/workspace");
      }, 1000);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to activate plan.");
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
                background: "rgba(99, 102, 241, 0.12)",
                color: "#818cf8",
                border: "1px solid rgba(99, 102, 241, 0.25)",
              }}
            >
              Paddle Merchant of Record
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

          {/* Billing Cycle Toggle */}
          <div className="inline-flex items-center p-1 rounded-xl border mt-6" style={{ background: "var(--card)", borderColor: "var(--border)" }}>
            <button
              onClick={() => setBillingCycle("monthly")}
              className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                billingCycle === "monthly" ? "bg-[var(--accent)] text-white shadow-md" : "text-[var(--txt-m)]"
              }`}
            >
              Monthly Billing
            </button>
            <button
              onClick={() => setBillingCycle("annual")}
              className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                billingCycle === "annual" ? "bg-[var(--accent)] text-white shadow-md" : "text-[var(--txt-m)]"
              }`}
            >
              <span>Annual Billing</span>
              <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-emerald-500 text-white font-mono">
                Save 20%
              </span>
            </button>
          </div>
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
              const price = billingCycle === "monthly" ? p.priceMonthly : p.priceAnnual;
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
                <span>Paddle Certified Checkout</span>
              </div>
              <p className="text-[11px]" style={{ color: "var(--txt-m)" }}>
                Payments, sales tax, VAT, and invoices are handled securely by Paddle.com. Cancel anytime with 1-click.
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
                  <span className="text-xs font-normal" style={{ color: "var(--txt-m)" }}>
                    /mo
                  </span>
                </div>
                <span className="text-[10px] font-mono text-emerald-500 font-bold">
                  {billingCycle === "annual" ? "Billed Annually ($" + currentPrice * 12 + "/yr)" : "Billed Monthly"}
                </span>
              </div>
            </div>

            {/* Included Features */}
            <div>
              <h4 className="text-xs font-mono uppercase font-bold mb-3" style={{ color: "var(--txt-m)" }}>
                Included Capabilities & Entitlements:
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
                <Zap size={16} />
                <span>{isLoading ? "Activating Plan..." : `⚡ Activate ${plan.name} (Pre-Deployment: No Payment Required)`}</span>
                <ArrowRight size={16} />
              </button>

              <div className="text-center pt-2">
                <p className="text-[11px] font-mono text-emerald-400">
                  ✓ Pre-deployment mode active: All tiers unlocked for free testing before live deployment.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="mt-16 text-center text-xs border-t pt-6" style={{ borderColor: "var(--border)", color: "var(--txt-m)" }}>
        <p>DataForge Inc. · Powered by Paddle (Merchant of Record)</p>
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
