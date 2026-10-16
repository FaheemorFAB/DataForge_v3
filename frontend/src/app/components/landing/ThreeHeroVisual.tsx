"use client";

import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import gsap from "gsap";

/* ─── 1. 3D Floating Pie Chart Graphic ───────────────────────────────────── */
function PieChartGraphic({ isLight }: { isLight: boolean }) {
  const sliceRef = useRef<SVGGElement>(null);
  const containerRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!sliceRef.current) return;
    // Exploded slice levitation
    const tween = gsap.to(sliceRef.current, {
      x: 6,
      y: -6,
      duration: 2.2,
      ease: "sine.inOut",
      yoyo: true,
      repeat: -1,
    });
    return () => {
      tween.kill();
    };
  }, []);

  return (
    <svg
      ref={containerRef}
      viewBox="0 0 160 110"
      className="w-full h-24 overflow-visible drop-shadow-lg"
    >
      <defs>
        {/* Gradients */}
        <linearGradient id="pie-cyan" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#00f0ff" />
          <stop offset="100%" stopColor="#0284c7" />
        </linearGradient>
        <linearGradient id="pie-pink" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#ff007f" />
          <stop offset="100%" stopColor="#e11d48" />
        </linearGradient>
        <linearGradient id="pie-amber" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#fbbf24" />
          <stop offset="100%" stopColor="#d97706" />
        </linearGradient>
        <linearGradient id="pie-purple" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#c084fc" />
          <stop offset="100%" stopColor="#7c3aed" />
        </linearGradient>
        <linearGradient id="pie-emerald" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#34d399" />
          <stop offset="100%" stopColor="#059669" />
        </linearGradient>

        {/* 3D Depth Sides */}
        <linearGradient id="pie-depth-cyan" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#0284c7" />
          <stop offset="100%" stopColor="#0369a1" />
        </linearGradient>
        <linearGradient id="pie-depth-pink" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#e11d48" />
          <stop offset="100%" stopColor="#9f1239" />
        </linearGradient>
      </defs>

      {/* Shadow Base */}
      <ellipse
        cx="78"
        cy="86"
        rx="52"
        ry="18"
        fill={isLight ? "rgba(0,0,0,0.08)" : "rgba(0,240,255,0.12)"}
        filter="blur(4px)"
      />

      {/* 3D Extrusion Side Wall (Cyan) */}
      <path
        d="M 32 54 C 32 72, 124 72, 124 54 L 124 66 C 124 84, 32 84, 32 66 Z"
        fill="url(#pie-depth-cyan)"
        opacity="0.9"
      />

      {/* Main Base Pie Slices */}
      {/* Cyan Large Sector (0° to 170°) */}
      <path
        d="M 78 52 L 124 52 A 46 22 0 0 1 34 56 Z"
        fill="url(#pie-cyan)"
      />

      {/* Amber Sector */}
      <path
        d="M 78 52 L 34 56 A 46 22 0 0 1 48 38 Z"
        fill="url(#pie-amber)"
      />

      {/* Purple Sector */}
      <path
        d="M 78 52 L 48 38 A 46 22 0 0 1 76 30 Z"
        fill="url(#pie-purple)"
      />

      {/* Emerald Sector */}
      <path
        d="M 78 52 L 76 30 A 46 22 0 0 1 96 33 Z"
        fill="url(#pie-emerald)"
      />

      {/* Exploded Pink Slice (lifts slightly outwards in 3D) */}
      <g ref={sliceRef}>
        {/* Pink Extrusion Depth */}
        <path
          d="M 78 52 L 124 52 L 124 62 L 78 62 Z"
          fill="url(#pie-depth-pink)"
        />
        <path
          d="M 78 52 L 96 33 A 46 22 0 0 1 124 52 Z"
          fill="url(#pie-pink)"
        />
      </g>
    </svg>
  );
}

/* ─── 2. 3D Floating Predictive Trends Line Chart ────────────────────────── */
function TrendLineGraphic({ isLight }: { isLight: boolean }) {
  const lineRef = useRef<SVGPathElement>(null);

  useEffect(() => {
    if (!lineRef.current) return;
    const length = lineRef.current.getTotalLength();
    gsap.set(lineRef.current, {
      strokeDasharray: length,
      strokeDashoffset: length,
    });
    const tween = gsap.to(lineRef.current, {
      strokeDashoffset: 0,
      duration: 2.4,
      ease: "power2.out",
    });
    return () => {
      tween.kill();
    };
  }, []);

  return (
    <svg viewBox="0 0 160 110" className="w-full h-24 overflow-visible drop-shadow-lg">
      <defs>
        <linearGradient id="trend-line-g" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#38bdf8" />
          <stop offset="50%" stopColor="#a855f7" />
          <stop offset="100%" stopColor="#f43f5e" />
        </linearGradient>
        <linearGradient id="trend-area-g" x1="0" y1="0" x2="0" y2="1">
          <stop
            offset="0%"
            stopColor={isLight ? "#0284c7" : "#38bdf8"}
            stopOpacity={isLight ? "0.25" : "0.35"}
          />
          <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.0" />
        </linearGradient>
      </defs>

      {/* Grid Lines */}
      <line
        x1="18"
        y1="82"
        x2="142"
        y2="82"
        stroke={isLight ? "#e2e8f0" : "#334155"}
        strokeWidth="1"
        strokeDasharray="3 3"
      />
      <line
        x1="18"
        y1="52"
        x2="142"
        y2="52"
        stroke={isLight ? "#e2e8f0" : "#334155"}
        strokeWidth="1"
        strokeDasharray="3 3"
      />
      <line
        x1="18"
        y1="24"
        x2="142"
        y2="24"
        stroke={isLight ? "#e2e8f0" : "#334155"}
        strokeWidth="1"
        strokeDasharray="3 3"
      />

      {/* Area Fill */}
      <path
        d="M 22 72 Q 52 40, 74 58 T 118 36 T 140 22 L 140 82 L 22 82 Z"
        fill="url(#trend-area-g)"
      />

      {/* Trend Curve */}
      <path
        ref={lineRef}
        d="M 22 72 Q 52 40, 74 58 T 118 36 T 140 22"
        fill="none"
        stroke="url(#trend-line-g)"
        strokeWidth="3.5"
        strokeLinecap="round"
      />

      {/* Glowing Data Point Spheres */}
      {[
        { cx: 22, cy: 72, col: "#38bdf8" },
        { cx: 74, cy: 58, col: "#a855f7" },
        { cx: 118, cy: 36, col: "#ec4899" },
        { cx: 140, cy: 22, col: "#f43f5e" },
      ].map((pt, i) => (
        <g key={i}>
          <circle
            cx={pt.cx}
            cy={pt.cy}
            r="6"
            fill={pt.col}
            opacity="0.3"
            className="animate-pulse"
          />
          <circle cx={pt.cx} cy={pt.cy} r="3.5" fill="#ffffff" />
        </g>
      ))}
    </svg>
  );
}

/* ─── 3. 3D Floating Database Storage Graphic ────────────────────────────── */
function DatabaseGraphic({ isLight }: { isLight: boolean }) {
  const dbRef = useRef<SVGGElement>(null);

  useEffect(() => {
    if (!dbRef.current) return;
    const tween = gsap.to(dbRef.current, {
      y: -5,
      duration: 2.8,
      ease: "sine.inOut",
      yoyo: true,
      repeat: -1,
    });
    return () => {
      tween.kill();
    };
  }, []);

  return (
    <svg viewBox="0 0 160 110" className="w-full h-24 overflow-visible drop-shadow-lg">
      <defs>
        <linearGradient id="db-disc-cyan" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#00f0ff" />
          <stop offset="100%" stopColor="#0284c7" />
        </linearGradient>
        <linearGradient id="db-disc-gold" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#fbbf24" />
          <stop offset="100%" stopColor="#d97706" />
        </linearGradient>
        <linearGradient id="db-disc-pink" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#f43f5e" />
          <stop offset="100%" stopColor="#be123c" />
        </linearGradient>
        <linearGradient id="db-disc-emerald" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#34d399" />
          <stop offset="100%" stopColor="#059669" />
        </linearGradient>
      </defs>

      {/* Shadow Base */}
      <ellipse
        cx="80"
        cy="92"
        rx="40"
        ry="14"
        fill={isLight ? "rgba(0,0,0,0.08)" : "rgba(0,240,255,0.12)"}
        filter="blur(4px)"
      />

      <g ref={dbRef}>
        {/* Layer 3 (Bottom Disk - Emerald) */}
        <path
          d="M 44 68 C 44 80, 116 80, 116 68 L 116 78 C 116 90, 44 90, 44 78 Z"
          fill="url(#db-disc-emerald)"
        />
        <ellipse cx="80" cy="68" rx="36" ry="11" fill="url(#db-disc-emerald)" />

        {/* Layer 2 (Middle Disk - Magenta/Gold) */}
        <path
          d="M 44 48 C 44 60, 116 60, 116 48 L 116 58 C 116 70, 44 70, 44 58 Z"
          fill="url(#db-disc-pink)"
        />
        <ellipse cx="80" cy="48" rx="36" ry="11" fill="url(#db-disc-gold)" />

        {/* Layer 1 (Top Disk - Cyan) */}
        <path
          d="M 44 28 C 44 40, 116 40, 116 28 L 116 38 C 116 50, 44 50, 44 38 Z"
          fill="url(#db-disc-cyan)"
        />
        <ellipse cx="80" cy="28" rx="36" ry="11" fill="url(#db-disc-cyan)" />

        {/* LED Activity Indicators */}
        <circle cx="56" cy="36" r="2.5" fill="#ffffff" className="animate-pulse" />
        <circle cx="56" cy="56" r="2.5" fill="#fbbf24" className="animate-pulse" />
        <circle cx="56" cy="76" r="2.5" fill="#34d399" className="animate-pulse" />
      </g>
    </svg>
  );
}

/* ─── 4. 3D Floating Pipeline / DAG Branch Graphic ───────────────────────── */
function PipelineDagGraphic({ isLight }: { isLight: boolean }) {
  const packetRef1 = useRef<SVGCircleElement>(null);
  const packetRef2 = useRef<SVGCircleElement>(null);

  useEffect(() => {
    if (!packetRef1.current || !packetRef2.current) return;
    const t1 = gsap.to(packetRef1.current, {
      motionPath: undefined,
      x: 62,
      y: -24,
      duration: 1.8,
      ease: "power1.inOut",
      repeat: -1,
      yoyo: false,
    });
    const t2 = gsap.to(packetRef2.current, {
      x: 62,
      y: 24,
      duration: 2.1,
      ease: "power1.inOut",
      repeat: -1,
      yoyo: false,
    });
    return () => {
      t1.kill();
      t2.kill();
    };
  }, []);

  return (
    <svg viewBox="0 0 160 110" className="w-full h-24 overflow-visible drop-shadow-lg">
      <defs>
        <linearGradient id="dag-flow-1" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#00f0ff" />
          <stop offset="100%" stopColor="#10b981" />
        </linearGradient>
        <linearGradient id="dag-flow-2" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#00f0ff" />
          <stop offset="100%" stopColor="#f43f5e" />
        </linearGradient>
      </defs>

      {/* Curved Branching Pipelines */}
      <path
        d="M 38 55 C 68 55, 78 30, 114 30"
        fill="none"
        stroke="url(#dag-flow-1)"
        strokeWidth="3.5"
        strokeLinecap="round"
      />
      <path
        d="M 38 55 C 68 55, 78 80, 114 80"
        fill="none"
        stroke="url(#dag-flow-2)"
        strokeWidth="3.5"
        strokeLinecap="round"
      />

      {/* Traveling Data Packets */}
      <circle ref={packetRef1} cx="44" cy="55" r="3.5" fill="#ffffff" />
      <circle ref={packetRef2} cx="44" cy="55" r="3.5" fill="#ffffff" />

      {/* Left Input Node */}
      <g>
        <circle cx="34" cy="55" r="14" fill="#0284c7" />
        <circle cx="34" cy="55" r="8" fill="#00f0ff" />
      </g>

      {/* Top Output Node */}
      <g>
        <circle cx="120" cy="30" r="12" fill="#047857" />
        <circle cx="120" cy="30" r="7" fill="#10b981" />
      </g>

      {/* Bottom Output Node */}
      <g>
        <circle cx="120" cy="80" r="12" fill="#be123c" />
        <circle cx="120" cy="80" r="7" fill="#f43f5e" />
      </g>
    </svg>
  );
}

/* ─── Main Hero Section 2x2 Ecosystem with Three.js & GSAP ───────────────── */
export default function ThreeHeroVisual() {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const cardsRef = useRef<(HTMLDivElement | null)[]>([]);

  const [themeMode, setThemeMode] = useState<"light" | "dark">("dark");

  // Track active theme
  useEffect(() => {
    const updateTheme = () => {
      const currentTheme = document.documentElement.getAttribute("data-theme") || "dark";
      const isLight = [
        "light",
        "cupcake",
        "solarized",
        "lavender",
        "matcha",
      ].includes(currentTheme);
      setThemeMode(isLight ? "light" : "dark");
    };

    updateTheme();
    const observer = new MutationObserver(updateTheme);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });

    return () => observer.disconnect();
  }, []);

  // Three.js Background Particle Constellation
  useEffect(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;

    let animId: number;
    let renderer: THREE.WebGLRenderer;
    let scene: THREE.Scene;
    let camera: THREE.PerspectiveCamera;

    const width = container.clientWidth || 560;
    const height = container.clientHeight || 560;
    const isLight = themeMode === "light";

    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 100);
    camera.position.z = 24;

    try {
      renderer = new THREE.WebGLRenderer({
        canvas,
        alpha: true,
        antialias: true,
        powerPreference: "high-performance",
      });
      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    } catch (e) {
      console.warn("Three.js fallback:", e);
      return;
    }

    const particleCount = 40;
    const geo = new THREE.BufferGeometry();
    const pos = new Float32Array(particleCount * 3);
    const vel: { x: number; y: number; z: number }[] = [];

    for (let i = 0; i < particleCount; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 32;
      pos[i * 3 + 1] = (Math.random() - 0.5) * 32;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 12;

      vel.push({
        x: (Math.random() - 0.5) * 0.025,
        y: (Math.random() - 0.5) * 0.025,
        z: (Math.random() - 0.5) * 0.015,
      });
    }

    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));

    const mat = new THREE.PointsMaterial({
      color: isLight ? 0x0284c7 : 0x38bdf8,
      size: isLight ? 0.45 : 0.65,
      transparent: true,
      opacity: isLight ? 0.45 : 0.75,
      blending: isLight ? THREE.NormalBlending : THREE.AdditiveBlending,
    });

    const points = new THREE.Points(geo, mat);
    scene.add(points);

    let mouseX = 0;
    let mouseY = 0;

    const onPointerMove = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      mouseX = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouseY = -(((e.clientY - rect.top) / rect.height) * 2 - 1);
    };

    window.addEventListener("mousemove", onPointerMove);

    const animate = () => {
      animId = requestAnimationFrame(animate);
      const posAttr = geo.attributes.position as THREE.BufferAttribute;
      const posArr = posAttr.array as Float32Array;

      for (let i = 0; i < particleCount; i++) {
        posArr[i * 3] += vel[i].x;
        posArr[i * 3 + 1] += vel[i].y;
        posArr[i * 3 + 2] += vel[i].z;

        if (posArr[i * 3] > 16) posArr[i * 3] = -16;
        if (posArr[i * 3] < -16) posArr[i * 3] = 16;
        if (posArr[i * 3 + 1] > 16) posArr[i * 3 + 1] = -16;
        if (posArr[i * 3 + 1] < -16) posArr[i * 3 + 1] = 16;
      }

      posAttr.needsUpdate = true;
      camera.position.x += (mouseX * 1.5 - camera.position.x) * 0.05;
      camera.position.y += (mouseY * 1.5 - camera.position.y) * 0.05;
      camera.lookAt(scene.position);

      renderer.render(scene, camera);
    };

    animate();

    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("mousemove", onPointerMove);
      window.removeEventListener("resize", handleResize);
      cancelAnimationFrame(animId);
      renderer.dispose();
    };
  }, [themeMode]);

  // GSAP 3D Interactive Parallax Tilt for the 4 Cards
  const handleCardMouseMove = (e: React.MouseEvent<HTMLDivElement>, idx: number) => {
    const card = cardsRef.current[idx];
    if (!card) return;

    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const normX = (x / rect.width) * 2 - 1;
    const normY = (y / rect.height) * 2 - 1;

    gsap.to(card, {
      rotateY: normX * 10,
      rotateX: -normY * 10,
      scale: 1.03,
      duration: 0.4,
      ease: "power2.out",
      transformPerspective: 800,
    });
  };

  const handleCardMouseLeave = (idx: number) => {
    const card = cardsRef.current[idx];
    if (!card) return;

    gsap.to(card, {
      rotateX: 0,
      rotateY: 0,
      scale: 1,
      duration: 0.6,
      ease: "power2.out",
    });
  };

  const isLight = themeMode === "light";

  const cardsData = [
    {
      title: "Distribution Profiling",
      desc: "Categorical breakdown, skewness & null shares",
      pill: "100% Coverage",
      accent: "#00f0ff",
      graphic: <PieChartGraphic isLight={isLight} />,
    },
    {
      title: "Predictive Trends",
      desc: "AutoML forecasts & multi-horizon trajectory",
      pill: "Predict",
      accent: "#f43f5e",
      graphic: <TrendLineGraphic isLight={isLight} />,
    },
    {
      title: "Polyglot Storage",
      desc: "CSV, Parquet, Excel & SQL zero-copy reads",
      pill: "Ingest",
      accent: "#fbbf24",
      graphic: <DatabaseGraphic isLight={isLight} />,
    },
    {
      title: "Visual Pipelines",
      desc: "DAG-based joins, cleaning & automated transforms",
      pill: "Structure",
      accent: "#10b981",
      graphic: <PipelineDagGraphic isLight={isLight} />,
    },
  ];

  return (
    <div
      ref={containerRef}
      className="relative w-full max-w-[560px] flex items-center justify-center p-2 select-none"
    >
      {/* 1. Three.js Background Constellation Canvas */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full pointer-events-none z-0"
      />

      {/* 2. Soft Ambient Lighting Orb */}
      <div
        className="absolute w-[420px] h-[420px] rounded-full blur-[130px] pointer-events-none opacity-40 z-0"
        style={{
          background: isLight
            ? "radial-gradient(circle, rgba(56, 189, 248, 0.25) 0%, rgba(244, 63, 94, 0.15) 100%)"
            : "radial-gradient(circle, rgba(56, 189, 248, 0.35) 0%, rgba(168, 85, 247, 0.2) 100%)",
        }}
      />

      {/* 3. 2x2 Premium Glassmorphic Cards Ecosystem */}
      <div className="relative z-10 w-full grid grid-cols-1 sm:grid-cols-2 gap-4">
        {cardsData.map((c, i) => (
          <div
            key={i}
            ref={(el) => {
              cardsRef.current[i] = el;
            }}
            onMouseMove={(e) => handleCardMouseMove(e, i)}
            onMouseLeave={() => handleCardMouseLeave(i)}
            className="flex flex-col justify-between p-5 rounded-2xl border transition-all duration-300 backdrop-blur-xl group cursor-pointer relative overflow-hidden"
            style={{
              background: isLight ? "rgba(255, 255, 255, 0.9)" : "var(--card)",
              borderColor: isLight ? "#e2e8f0" : "var(--border)",
              boxShadow: isLight
                ? "0 10px 25px -5px rgba(0, 0, 0, 0.06), 0 0 1px rgba(0, 0, 0, 0.1)"
                : "0 16px 36px -8px rgba(0, 0, 0, 0.5), 0 0 20px rgba(56, 189, 248, 0.08)",
            }}
          >
            {/* Top Row: Pill Tag */}
            <div className="flex items-center justify-between w-full mb-1">
              <span
                className={`text-[10px] font-extrabold uppercase tracking-wider px-2.5 py-1 rounded-full border shadow-sm ${
                  isLight
                    ? "bg-slate-100 text-slate-900 border-slate-300"
                    : "bg-slate-900/90 text-cyan-300 border-cyan-500/30"
                }`}
              >
                {c.pill}
              </span>

              {/* Glowing Indicator Dot */}
              <div
                className="w-2 h-2 rounded-full"
                style={{
                  background: c.accent,
                  boxShadow: `0 0 8px ${c.accent}`,
                }}
              />
            </div>

            {/* Middle: 3D Animated Graphic */}
            <div className="py-2 flex items-center justify-center">
              {c.graphic}
            </div>

            {/* Bottom Row: Title & Subtitle with STRICT HIGH CONTRAST */}
            <div className="flex flex-col gap-1 mt-2 text-left">
              <h3
                className="text-sm font-black tracking-tight"
                style={{
                  color: isLight ? "#09090B" : "var(--txt)",
                }}
              >
                {c.title}
              </h3>
              <p
                className="text-[11px] font-semibold leading-snug line-clamp-2"
                style={{
                  color: isLight ? "#27272A" : "var(--txt-m)",
                }}
              >
                {c.desc}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
