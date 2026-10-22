"use client";

import { useState, useEffect } from "react";

export interface ChartThemeColors {
  text: string;
  textMuted: string;
  grid: string;
  border: string;
  isDark: boolean;
  tooltipBg: string;
  tooltipText: string;
  tooltipBorder: string;
}

const DARK_THEMES = new Set([
  "dark",
  "dracula",
  "slate",
  "emerald",
  "nord",
  "luxury",
  "night",
  "synthwave",
  "black",
  "cyber",
]);

export function getChartThemeColors(): ChartThemeColors {
  if (typeof window === "undefined") {
    return {
      text: "#000000",
      textMuted: "#0f172a",
      grid: "rgba(0,0,0,0.06)",
      border: "#cbd5e1",
      isDark: false,
      tooltipBg: "rgba(15,23,42,0.95)",
      tooltipText: "#ffffff",
      tooltipBorder: "rgba(99,102,241,0.4)",
    };
  }

  const root = document.documentElement;
  const currentTheme = root.getAttribute("data-theme") || "dark";
  const isDark = DARK_THEMES.has(currentTheme.toLowerCase());

  let computedTxt = "";
  let computedTxtM = "";
  try {
    const cs = getComputedStyle(root);
    computedTxt = cs.getPropertyValue("--txt").trim();
    computedTxtM = cs.getPropertyValue("--txt-m").trim();
  } catch {}

  const text = computedTxt || (isDark ? "#FFFFFF" : "#000000");
  const textMuted = computedTxtM || (isDark ? "#E2E8F0" : "#0F172A");
  const grid = isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)";
  const border = isDark ? "rgba(255,255,255,0.18)" : "rgba(0,0,0,0.12)";

  return {
    text,
    textMuted,
    grid,
    border,
    isDark,
    tooltipBg: isDark ? "rgba(15,23,42,0.95)" : "rgba(255,255,255,0.98)",
    tooltipText: isDark ? "#ffffff" : "#000000",
    tooltipBorder: isDark ? "rgba(99,102,241,0.4)" : "rgba(0,0,0,0.15)",
  };
}

export function useChartTheme(): ChartThemeColors {
  const [colors, setColors] = useState<ChartThemeColors>(getChartThemeColors);

  useEffect(() => {
    const root = document.documentElement;
    const observer = new MutationObserver(() => {
      setColors(getChartThemeColors());
    });

    observer.observe(root, {
      attributes: true,
      attributeFilter: ["data-theme", "style", "class"],
    });

    return () => observer.disconnect();
  }, []);

  return colors;
}
