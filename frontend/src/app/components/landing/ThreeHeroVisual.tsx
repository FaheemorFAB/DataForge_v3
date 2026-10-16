"use client";

import React, { useEffect, useRef, useState } from "react";
import Image from "next/image";
import * as THREE from "three";
import gsap from "gsap";

export default function ThreeHeroVisual() {
  const containerRef = useRef<HTMLDivElement>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const glareRef = useRef<HTMLDivElement>(null);

  const [themeMode, setThemeMode] = useState<"light" | "dark">("dark");
  const [activeBadge, setActiveBadge] = useState<string | null>(null);

  // Synchronize with active theme
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

  // Three.js interactive ambient particle constellation behind 3D artwork
  useEffect(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;

    let animationFrameId: number;
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

    // Particle constellation
    const particleCount = 45;
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const velocities: { x: number; y: number; z: number }[] = [];

    for (let i = 0; i < particleCount; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 32;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 32;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 12;

      velocities.push({
        x: (Math.random() - 0.5) * 0.03,
        y: (Math.random() - 0.5) * 0.03,
        z: (Math.random() - 0.5) * 0.02,
      });
    }

    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));

    const material = new THREE.PointsMaterial({
      color: isLight ? 0x0284c7 : 0x38bdf8,
      size: isLight ? 0.45 : 0.65,
      transparent: true,
      opacity: isLight ? 0.45 : 0.75,
      blending: isLight ? THREE.NormalBlending : THREE.AdditiveBlending,
    });

    const particles = new THREE.Points(geometry, material);
    scene.add(particles);

    // Glowing connecting line segments between nearby particles
    const lineMat = new THREE.LineBasicMaterial({
      color: isLight ? 0x0284c7 : 0xa855f7,
      transparent: true,
      opacity: isLight ? 0.15 : 0.25,
      blending: isLight ? THREE.NormalBlending : THREE.AdditiveBlending,
    });

    const lineGeo = new THREE.BufferGeometry();
    const maxLineSegments = particleCount * 4;
    const linePositions = new Float32Array(maxLineSegments * 6);
    lineGeo.setAttribute("position", new THREE.BufferAttribute(linePositions, 3));
    const lines = new THREE.LineSegments(lineGeo, lineMat);
    scene.add(lines);

    let mouseX = 0;
    let mouseY = 0;

    const onPointerMove = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      mouseX = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouseY = -(((e.clientY - rect.top) / rect.height) * 2 - 1);
    };

    window.addEventListener("mousemove", onPointerMove);

    const clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const elapsed = clock.getElapsedTime();

      // Smooth particle drift
      const posAttr = geometry.attributes.position as THREE.BufferAttribute;
      const posArr = posAttr.array as Float32Array;

      let lineIdx = 0;
      const linePosArr = (lineGeo.attributes.position as THREE.BufferAttribute).array as Float32Array;

      for (let i = 0; i < particleCount; i++) {
        posArr[i * 3] += velocities[i].x;
        posArr[i * 3 + 1] += velocities[i].y;
        posArr[i * 3 + 2] += velocities[i].z;

        // Boundary wrap
        if (posArr[i * 3] > 16) posArr[i * 3] = -16;
        if (posArr[i * 3] < -16) posArr[i * 3] = 16;
        if (posArr[i * 3 + 1] > 16) posArr[i * 3 + 1] = -16;
        if (posArr[i * 3 + 1] < -16) posArr[i * 3 + 1] = 16;

        // Connect lines
        for (let j = i + 1; j < particleCount; j++) {
          const dx = posArr[i * 3] - posArr[j * 3];
          const dy = posArr[i * 3 + 1] - posArr[j * 3 + 1];
          const dz = posArr[i * 3 + 2] - posArr[j * 3 + 2];
          const distSq = dx * dx + dy * dy + dz * dz;

          if (distSq < 36 && lineIdx < maxLineSegments * 6 - 6) {
            linePosArr[lineIdx++] = posArr[i * 3];
            linePosArr[lineIdx++] = posArr[i * 3 + 1];
            linePosArr[lineIdx++] = posArr[i * 3 + 2];
            linePosArr[lineIdx++] = posArr[j * 3];
            linePosArr[lineIdx++] = posArr[j * 3 + 1];
            linePosArr[lineIdx++] = posArr[j * 3 + 2];
          }
        }
      }

      posAttr.needsUpdate = true;
      lineGeo.setDrawRange(0, lineIdx / 3);
      (lineGeo.attributes.position as THREE.BufferAttribute).needsUpdate = true;

      // Gentle camera reaction
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
      cancelAnimationFrame(animationFrameId);
      renderer.dispose();
    };
  }, [themeMode]);

  // GSAP 3D Interactive Parallax & Subtle Levitation on the 3D card
  useEffect(() => {
    const card = cardRef.current;
    const container = containerRef.current;
    const glare = glareRef.current;
    if (!card || !container) return;

    // Continuous floating levitation
    const floatTween = gsap.to(card, {
      y: -10,
      duration: 3.2,
      ease: "sine.inOut",
      yoyo: true,
      repeat: -1,
    });

    const handleMouseMove = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      const normX = (x / rect.width) * 2 - 1;
      const normY = (y / rect.height) * 2 - 1;

      // GSAP smooth 3D tilt
      gsap.to(card, {
        rotateY: normX * 14,
        rotateX: -normY * 14,
        scale: 1.02,
        duration: 0.8,
        ease: "power2.out",
        transformPerspective: 1200,
        transformOrigin: "center center",
      });

      // Specular glare position
      if (glare) {
        const glareX = (x / rect.width) * 100;
        const glareY = (y / rect.height) * 100;
        gsap.to(glare, {
          background: `radial-gradient(circle 350px at ${glareX}% ${glareY}%, ${
            themeMode === "light"
              ? "rgba(255, 255, 255, 0.45)"
              : "rgba(56, 189, 248, 0.18)"
          }, transparent 70%)`,
          duration: 0.3,
        });
      }
    };

    const handleMouseLeave = () => {
      gsap.to(card, {
        rotateX: 0,
        rotateY: 0,
        scale: 1,
        duration: 1.2,
        ease: "power2.out",
      });
      if (glare) {
        gsap.to(glare, {
          background: "transparent",
          duration: 0.8,
        });
      }
    };

    container.addEventListener("mousemove", handleMouseMove);
    container.addEventListener("mouseleave", handleMouseLeave);

    return () => {
      floatTween.kill();
      container.removeEventListener("mousemove", handleMouseMove);
      container.removeEventListener("mouseleave", handleMouseLeave);
    };
  }, [themeMode]);

  const isLight = themeMode === "light";

  const badges = [
    {
      id: "ingest",
      label: "✦ Ingest",
      desc: "Fast streaming of CSV, Excel, Parquet & SQL",
      pos: "top-4 left-1/2 -translate-x-1/2",
    },
    {
      id: "structure",
      label: "✦ Structure",
      desc: "Instant schema inference & anomaly detection",
      pos: "top-1/3 left-2 sm:left-4",
    },
    {
      id: "predict",
      label: "✦ Predict",
      desc: "AutoML models & predictive forecasting",
      pos: "top-1/3 right-2 sm:right-4",
    },
    {
      id: "insight",
      label: "✦ Insight",
      desc: "Executive visual dashboards & AI reports",
      pos: "bottom-4 left-1/2 -translate-x-1/2",
    },
  ];

  return (
    <div
      ref={containerRef}
      className="relative w-full max-w-[540px] aspect-square flex items-center justify-center select-none"
    >
      {/* 1. Three.js Background Particle Constellation */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full pointer-events-none z-0"
      />

      {/* 2. Ambient Glow Orb */}
      <div
        className="absolute w-[360px] h-[360px] rounded-full blur-[110px] pointer-events-none transition-all duration-700 opacity-60 z-0"
        style={{
          background: isLight
            ? "radial-gradient(circle, rgba(56, 189, 248, 0.25) 0%, rgba(244, 63, 94, 0.15) 100%)"
            : "radial-gradient(circle, rgba(56, 189, 248, 0.35) 0%, rgba(168, 85, 247, 0.25) 100%)",
        }}
      />

      {/* 3. Central 3D Glassmorphic Masterpiece Card with GSAP Parallax */}
      <div
        ref={cardRef}
        className="relative z-10 w-[88%] aspect-square rounded-[2.5rem] p-1.5 transition-shadow duration-500 overflow-hidden"
        style={{
          boxShadow: isLight
            ? "0 30px 60px -15px rgba(0, 0, 0, 0.12), 0 0 40px rgba(56, 189, 248, 0.15)"
            : "0 30px 70px -15px rgba(0, 0, 0, 0.65), 0 0 50px rgba(56, 189, 248, 0.25)",
        }}
      >
        {/* Specular Interactive Glass Glare */}
        <div
          ref={glareRef}
          className="absolute inset-0 pointer-events-none z-20 rounded-[2.5rem] transition-opacity duration-300"
        />

        {/* 3D Image Artwork: Switches seamlessly between Light and Dark */}
        <div className="relative w-full h-full rounded-[2.2rem] overflow-hidden">
          <Image
            src={isLight ? "/hero_3d_light.jpg" : "/hero_3d_dark.jpg"}
            alt="DataForge 3D Analytics Ecosystem"
            fill
            priority
            sizes="(max-width: 768px) 100vw, 540px"
            className="object-cover transition-opacity duration-500"
          />
        </div>
      </div>

      {/* 4. Interactive Floating Pills along the Orbit */}
      {badges.map((b) => {
        const isHovered = activeBadge === b.id;
        return (
          <div
            key={b.id}
            onMouseEnter={() => setActiveBadge(b.id)}
            onMouseLeave={() => setActiveBadge(null)}
            className={`absolute z-30 ${b.pos} cursor-pointer transition-all duration-300`}
          >
            <div
              className={`px-3.5 py-1.5 rounded-full text-xs font-black tracking-wide border shadow-xl backdrop-blur-xl transition-all duration-300 hover:scale-108 ${
                isLight
                  ? "bg-white/95 text-slate-900 border-slate-300 shadow-slate-300/50 hover:border-sky-500"
                  : "bg-slate-900/85 text-cyan-300 border-cyan-500/40 shadow-cyan-500/25 hover:border-cyan-400"
              }`}
            >
              {b.label}
            </div>

            {/* Hover Tooltip explaining the node */}
            {isHovered && (
              <div
                className={`absolute left-1/2 -translate-x-1/2 mt-2 px-3 py-1.5 rounded-xl text-[11px] font-bold whitespace-nowrap shadow-2xl border backdrop-blur-2xl transition-all duration-200 z-40 ${
                  isLight
                    ? "bg-slate-900 text-white border-slate-700"
                    : "bg-white text-slate-950 border-slate-200"
                }`}
              >
                {b.desc}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
