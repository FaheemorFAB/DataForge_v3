"use client";

import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";

interface ThemePalette {
  name: string;
  isLight: boolean;
  accent: string;
  palette: [string, string, string, string, string]; // [primary, secondary, tertiary, highlight, glassTint]
  bgGlow: string;
  cardGlassColor: number;
  cardGlassOpacity: number;
}

const THEME_PALETTES: Record<string, ThemePalette> = {
  dark: {
    name: "dark",
    isLight: false,
    accent: "#FF4310",
    palette: ["#FF4310", "#00F0FF", "#A855F7", "#10B981", "#FBBF24"],
    bgGlow: "rgba(255, 67, 16, 0.22)",
    cardGlassColor: 0x111118,
    cardGlassOpacity: 0.65,
  },
  light: {
    name: "light",
    isLight: true,
    accent: "#FF4310",
    palette: ["#FF4310", "#0284C7", "#7C3AED", "#059669", "#F59E0B"],
    bgGlow: "rgba(255, 67, 16, 0.16)",
    cardGlassColor: 0xffffff,
    cardGlassOpacity: 0.85,
  },
  dracula: {
    name: "dracula",
    isLight: false,
    accent: "#BD93F9",
    palette: ["#BD93F9", "#FF79C6", "#8BE9FD", "#50FA7B", "#FFB86C"],
    bgGlow: "rgba(189, 147, 249, 0.26)",
    cardGlassColor: 0x282a36,
    cardGlassOpacity: 0.7,
  },
  slate: {
    name: "slate",
    isLight: false,
    accent: "#38BDF8",
    palette: ["#38BDF8", "#818CF8", "#34D399", "#C084FC", "#FB7185"],
    bgGlow: "rgba(56, 189, 248, 0.24)",
    cardGlassColor: 0x1e293b,
    cardGlassOpacity: 0.7,
  },
  emerald: {
    name: "emerald",
    isLight: false,
    accent: "#10B981",
    palette: ["#10B981", "#34D399", "#06B6D4", "#F59E0B", "#6EE7B7"],
    bgGlow: "rgba(16, 185, 129, 0.24)",
    cardGlassColor: 0x0d2820,
    cardGlassOpacity: 0.7,
  },
  nord: {
    name: "nord",
    isLight: false,
    accent: "#88C0D0",
    palette: ["#88C0D0", "#81A1C1", "#8FBCBB", "#A3BE8C", "#EBCB8B"],
    bgGlow: "rgba(136, 192, 208, 0.25)",
    cardGlassColor: 0x2e3440,
    cardGlassOpacity: 0.7,
  },
  luxury: {
    name: "luxury",
    isLight: false,
    accent: "#EAB308",
    palette: ["#EAB308", "#F59E0B", "#FDE047", "#CA8A04", "#FFFFFF"],
    bgGlow: "rgba(234, 179, 8, 0.26)",
    cardGlassColor: 0x18181b,
    cardGlassOpacity: 0.75,
  },
  cupcake: {
    name: "cupcake",
    isLight: true,
    accent: "#DB2777",
    palette: ["#DB2777", "#F43F5E", "#8B5CF6", "#0284C7", "#F59E0B"],
    bgGlow: "rgba(219, 39, 119, 0.2)",
    cardGlassColor: 0xffffff,
    cardGlassOpacity: 0.88,
  },
  solarized: {
    name: "solarized",
    isLight: true,
    accent: "#2AA198",
    palette: ["#2AA198", "#B58900", "#268BD2", "#D33682", "#859900"],
    bgGlow: "rgba(42, 161, 152, 0.2)",
    cardGlassColor: 0xeee8d5,
    cardGlassOpacity: 0.88,
  },
  lavender: {
    name: "lavender",
    isLight: true,
    accent: "#7C3AED",
    palette: ["#7C3AED", "#6366F1", "#EC4899", "#06B6D4", "#F59E0B"],
    bgGlow: "rgba(124, 58, 237, 0.2)",
    cardGlassColor: 0xffffff,
    cardGlassOpacity: 0.88,
  },
  matcha: {
    name: "matcha",
    isLight: true,
    accent: "#15803D",
    palette: ["#15803D", "#059669", "#65A30D", "#0D9488", "#10B981"],
    bgGlow: "rgba(21, 128, 61, 0.2)",
    cardGlassColor: 0xffffff,
    cardGlassOpacity: 0.88,
  },
};

function createRoundedRectShape(width: number, height: number, radius: number) {
  const shape = new THREE.Shape();
  const x = -width / 2;
  const y = -height / 2;
  shape.moveTo(x, y + radius);
  shape.lineTo(x, y + height - radius);
  shape.quadraticCurveTo(x, y + height, x + radius, y + height);
  shape.lineTo(x + width - radius, y + height);
  shape.quadraticCurveTo(x + width, y + height, x + width, y + height - radius);
  shape.lineTo(x + width, y + radius);
  shape.quadraticCurveTo(x + width, y, x + width - radius, y);
  shape.lineTo(x + radius, y);
  shape.quadraticCurveTo(x, y, x, y + radius);
  return shape;
}

function createPieSliceGeometry(startAngle: number, endAngle: number, radius: number, depth: number) {
  const shape = new THREE.Shape();
  shape.moveTo(0, 0);
  shape.absarc(0, 0, radius, startAngle, endAngle, false);
  shape.lineTo(0, 0);
  return new THREE.ExtrudeGeometry(shape, {
    depth,
    bevelEnabled: true,
    bevelSegments: 2,
    steps: 1,
    bevelSize: 0.04,
    bevelThickness: 0.04,
  });
}

export default function ThreeHeroVisual() {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [currentTheme, setCurrentTheme] = useState<string>("dark");

  // Track theme changes dynamically
  useEffect(() => {
    const readTheme = () => {
      const t = document.documentElement.getAttribute("data-theme") || "dark";
      setCurrentTheme(t);
    };

    readTheme();
    const observer = new MutationObserver(readTheme);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });

    return () => observer.disconnect();
  }, []);

  // Main Three.js real-time 3D Analytics scene with full Mobile Responsiveness
  useEffect(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;

    let animId: number;
    const width = container.clientWidth || 540;
    const height = container.clientHeight || 540;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);

    // Initial camera position & responsive scale
    const isMobile = width < 560;
    camera.position.set(0, 0, isMobile ? 16.5 : 15.0);

    let renderer: THREE.WebGLRenderer;
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
      console.warn("WebGL initialization fallback:", e);
      return;
    }

    const activeTheme = THEME_PALETTES[currentTheme] || THEME_PALETTES.dark;
    const p = activeTheme.palette;

    // Root Master Group for Parallax Tilt & Mobile Scale Fitting
    const masterGroup = new THREE.Group();
    const initialScale = isMobile ? Math.min(1.0, Math.max(0.66, width / 510)) : 1.0;
    masterGroup.scale.set(initialScale, initialScale, initialScale);
    scene.add(masterGroup);

    // Dynamic Lights
    const ambientLight = new THREE.AmbientLight(
      0xffffff,
      activeTheme.isLight ? 2.0 : 1.3
    );
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 2.2);
    dirLight.position.set(6, 8, 12);
    scene.add(dirLight);

    const rimLight = new THREE.DirectionalLight(new THREE.Color(p[0]), 1.4);
    rimLight.position.set(-6, -6, -6);
    scene.add(rimLight);

    const cursorPointLight = new THREE.PointLight(new THREE.Color(p[1]), 2.2, 18);
    cursorPointLight.position.set(0, 0, 8);
    scene.add(cursorPointLight);

    // ==========================================
    // 1. CENTRAL 3D PIE CHART WITH EXPLODED SLICE
    // ==========================================
    const centerGroup = new THREE.Group();
    centerGroup.position.set(0, 0, 0);
    masterGroup.add(centerGroup);

    // Central Frosted Glass Stage / Backing Plaque
    const centerStageGeo = new THREE.ExtrudeGeometry(
      createRoundedRectShape(3.8, 3.8, 0.65),
      {
        depth: 0.12,
        bevelEnabled: true,
        bevelSegments: 2,
        steps: 1,
        bevelSize: 0.04,
        bevelThickness: 0.04,
      }
    );
    centerStageGeo.center();

    const centerStageMat = new THREE.MeshPhysicalMaterial({
      color: activeTheme.cardGlassColor,
      roughness: 0.12,
      metalness: 0.05,
      transmission: 0.85,
      transparent: true,
      opacity: activeTheme.cardGlassOpacity,
      ior: 1.5,
      clearcoat: 1.0,
      clearcoatRoughness: 0.08,
      reflectivity: 0.9,
    });
    const centerStage = new THREE.Mesh(centerStageGeo, centerStageMat);
    centerStage.position.z = -0.15;
    centerGroup.add(centerStage);

    // Central Inner Glowing Core Ring
    const coreRingGeo = new THREE.TorusGeometry(0.35, 0.05, 16, 32);
    const coreRingMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(p[0]),
      emissive: new THREE.Color(p[0]),
      emissiveIntensity: 0.8,
      roughness: 0.2,
      metalness: 0.4,
    });
    const coreRing = new THREE.Mesh(coreRingGeo, coreRingMat);
    coreRing.position.z = 0.42;
    centerGroup.add(coreRing);

    // 4 Pie Slices
    const pieRadius = 1.65;
    const pieDepth = 0.42;

    const sliceMats = [
      new THREE.MeshPhysicalMaterial({
        color: new THREE.Color(p[0]),
        emissive: new THREE.Color(p[0]),
        emissiveIntensity: 0.25,
        roughness: 0.15,
        metalness: 0.15,
        clearcoat: 0.9,
        clearcoatRoughness: 0.1,
      }),
      new THREE.MeshPhysicalMaterial({
        color: new THREE.Color(p[1]),
        emissive: new THREE.Color(p[1]),
        emissiveIntensity: 0.25,
        roughness: 0.15,
        metalness: 0.15,
        clearcoat: 0.9,
        clearcoatRoughness: 0.1,
      }),
      new THREE.MeshPhysicalMaterial({
        color: new THREE.Color(p[2]),
        emissive: new THREE.Color(p[2]),
        emissiveIntensity: 0.25,
        roughness: 0.15,
        metalness: 0.15,
        clearcoat: 0.9,
        clearcoatRoughness: 0.1,
      }),
      new THREE.MeshPhysicalMaterial({
        color: new THREE.Color(p[3]),
        emissive: new THREE.Color(p[3]),
        emissiveIntensity: 0.35,
        roughness: 0.15,
        metalness: 0.15,
        clearcoat: 1.0,
        clearcoatRoughness: 0.08,
      }),
    ];

    // Slice 0
    const slice0Geo = createPieSliceGeometry(0.08, 1.85, pieRadius, pieDepth);
    const slice0 = new THREE.Mesh(slice0Geo, sliceMats[0]);
    centerGroup.add(slice0);

    // Slice 1
    const slice1Geo = createPieSliceGeometry(1.95, 3.42, pieRadius, pieDepth);
    const slice1 = new THREE.Mesh(slice1Geo, sliceMats[1]);
    centerGroup.add(slice1);

    // Slice 2
    const slice2Geo = createPieSliceGeometry(3.52, 4.92, pieRadius, pieDepth);
    const slice2 = new THREE.Mesh(slice2Geo, sliceMats[2]);
    centerGroup.add(slice2);

    // Slice 3: The Exploded Highlight Slice
    const slice3Geo = createPieSliceGeometry(5.02, 6.2, pieRadius, pieDepth);
    const slice3 = new THREE.Mesh(slice3Geo, sliceMats[3]);
    const slice3Angle = (5.02 + 6.2) / 2;
    slice3.position.x = Math.cos(slice3Angle) * 0.38;
    slice3.position.y = Math.sin(slice3Angle) * 0.38;
    slice3.position.z = 0.22;
    centerGroup.add(slice3);

    // ==========================================
    // 2. FLOATING BADGE 1: 3D BAR CHART (TOP-LEFT)
    // ==========================================
    const barWidget = new THREE.Group();
    barWidget.position.set(-3.4, 2.2, 0.7);
    masterGroup.add(barWidget);

    const widgetPlateGeo = new THREE.ExtrudeGeometry(
      createRoundedRectShape(2.2, 1.8, 0.32),
      {
        depth: 0.08,
        bevelEnabled: true,
        bevelSegments: 2,
        steps: 1,
        bevelSize: 0.03,
        bevelThickness: 0.03,
      }
    );
    widgetPlateGeo.center();

    const widgetPlateMat = new THREE.MeshPhysicalMaterial({
      color: activeTheme.cardGlassColor,
      roughness: 0.14,
      metalness: 0.05,
      transmission: 0.85,
      transparent: true,
      opacity: activeTheme.cardGlassOpacity,
      ior: 1.5,
      clearcoat: 1.0,
      clearcoatRoughness: 0.1,
    });

    const barPlate = new THREE.Mesh(widgetPlateGeo, widgetPlateMat);
    barPlate.position.z = -0.05;
    barWidget.add(barPlate);

    // 4 Animated Vertical Bars
    const barHeights = [0.55, 1.25, 0.85, 1.45];
    const barMeshes: THREE.Mesh[] = [];
    for (let i = 0; i < 4; i++) {
      const bh = barHeights[i];
      const barGeo = new THREE.BoxGeometry(0.24, bh, 0.2);
      barGeo.translate(0, bh / 2, 0); // anchor at bottom
      const barMat = new THREE.MeshStandardMaterial({
        color: new THREE.Color(p[i % p.length]),
        emissive: new THREE.Color(p[i % p.length]),
        emissiveIntensity: 0.3,
        roughness: 0.2,
        metalness: 0.3,
      });
      const barMesh = new THREE.Mesh(barGeo, barMat);
      barMesh.position.set(-0.6 + i * 0.4, -0.7, 0.08);
      barWidget.add(barMesh);
      barMeshes.push(barMesh);
    }

    // ==========================================
    // 3. FLOATING BADGE 2: 3D TREND LINE (TOP-RIGHT)
    // ==========================================
    const trendWidget = new THREE.Group();
    trendWidget.position.set(3.4, 2.1, 0.6);
    masterGroup.add(trendWidget);

    const trendPlate = new THREE.Mesh(widgetPlateGeo, widgetPlateMat.clone());
    trendPlate.position.z = -0.05;
    trendWidget.add(trendPlate);

    // 3D Neon Tube Spline Curve
    const trendCurve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(-0.75, -0.45, 0.1),
      new THREE.Vector3(-0.35, -0.15, 0.14),
      new THREE.Vector3(0.05, -0.28, 0.12),
      new THREE.Vector3(0.42, 0.22, 0.18),
      new THREE.Vector3(0.75, 0.55, 0.22),
    ]);
    const trendGeo = new THREE.TubeGeometry(trendCurve, 32, 0.045, 12, false);
    const trendMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(p[1]),
      emissive: new THREE.Color(p[1]),
      emissiveIntensity: 0.85,
      roughness: 0.15,
      metalness: 0.4,
    });
    const trendMesh = new THREE.Mesh(trendGeo, trendMat);
    trendWidget.add(trendMesh);

    // Glowing Peak Beacon
    const beaconGeo = new THREE.SphereGeometry(0.1, 16, 16);
    const beaconMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(p[3]),
      emissive: new THREE.Color(p[3]),
      emissiveIntensity: 1.0,
      roughness: 0.1,
    });
    const beaconMesh = new THREE.Mesh(beaconGeo, beaconMat);
    beaconMesh.position.set(0.75, 0.55, 0.22);
    trendWidget.add(beaconMesh);

    // ==========================================
    // 4. FLOATING BADGE 3: 3D POLYGLOT DB (BOTTOM-LEFT)
    // ==========================================
    const dbWidget = new THREE.Group();
    dbWidget.position.set(-3.3, -2.1, 0.65);
    masterGroup.add(dbWidget);

    const dbPlate = new THREE.Mesh(widgetPlateGeo, widgetPlateMat.clone());
    dbPlate.position.z = -0.05;
    dbWidget.add(dbPlate);

    // 3 Stacked Cylindrical Database Platters
    const dbDisks: THREE.Mesh[] = [];
    const dbDiskY = [-0.4, 0.0, 0.4];
    for (let i = 0; i < 3; i++) {
      const diskGeo = new THREE.CylinderGeometry(0.58, 0.58, 0.2, 32);
      const diskMat = new THREE.MeshPhysicalMaterial({
        color: new THREE.Color(p[i === 1 ? 0 : 1]),
        emissive: new THREE.Color(p[i === 1 ? 0 : 1]),
        emissiveIntensity: 0.35,
        roughness: 0.18,
        metalness: 0.25,
        clearcoat: 0.9,
      });
      const disk = new THREE.Mesh(diskGeo, diskMat);
      disk.rotation.x = 0.35;
      disk.position.set(0, dbDiskY[i], 0.12);
      dbWidget.add(disk);
      dbDisks.push(disk);
    }

    // ==========================================
    // 5. FLOATING BADGE 4: 3D DATA MATRIX (BOTTOM-RIGHT)
    // ==========================================
    const matrixWidget = new THREE.Group();
    matrixWidget.position.set(3.3, -2.1, 0.7);
    masterGroup.add(matrixWidget);

    const matrixPlate = new THREE.Mesh(widgetPlateGeo, widgetPlateMat.clone());
    matrixPlate.position.z = -0.05;
    matrixWidget.add(matrixPlate);

    // 3 rows x 4 columns of glowing mini tiles
    const matrixCells: THREE.Mesh[] = [];
    const matrixMats: THREE.MeshStandardMaterial[] = [];
    const rows = 3;
    const cols = 4;
    const cellW = 0.32;
    const cellH = 0.24;

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const cellGeo = new THREE.BoxGeometry(cellW, cellH, 0.08);
        const paletteIdx = (r * cols + c) % p.length;
        const cMat = new THREE.MeshStandardMaterial({
          color: new THREE.Color(p[paletteIdx]),
          emissive: new THREE.Color(p[paletteIdx]),
          emissiveIntensity: 0.35 + ((r + c) % 3) * 0.2,
          roughness: 0.2,
          metalness: 0.2,
        });
        const cellMesh = new THREE.Mesh(cellGeo, cMat);
        const xPos = -0.6 + c * (cellW + 0.08);
        const yPos = 0.36 - r * (cellH + 0.1);
        cellMesh.position.set(xPos, yPos, 0.1);
        matrixWidget.add(cellMesh);
        matrixCells.push(cellMesh);
        matrixMats.push(cMat);
      }
    }

    // ==========================================
    // 6. 3D ORBITAL RINGS & ENERGY SPARKS
    // ==========================================
    const orbitGroup = new THREE.Group();
    masterGroup.add(orbitGroup);

    const ring1Geo = new THREE.TorusGeometry(4.7, 0.02, 16, 120);
    const ring1Mat = new THREE.MeshBasicMaterial({
      color: new THREE.Color(p[1]),
      transparent: true,
      opacity: activeTheme.isLight ? 0.35 : 0.65,
    });
    const ring1 = new THREE.Mesh(ring1Geo, ring1Mat);
    ring1.rotation.set(1.15, 0.35, 0.2);
    orbitGroup.add(ring1);

    const ring2Geo = new THREE.TorusGeometry(4.3, 0.018, 16, 120);
    const ring2Mat = new THREE.MeshBasicMaterial({
      color: new THREE.Color(p[2]),
      transparent: true,
      opacity: activeTheme.isLight ? 0.3 : 0.6,
    });
    const ring2 = new THREE.Mesh(ring2Geo, ring2Mat);
    ring2.rotation.set(-0.95, -0.55, 0.45);
    orbitGroup.add(ring2);

    // Glowing energy nodes traveling on the orbits
    const sparkGeo = new THREE.SphereGeometry(0.11, 16, 16);
    const spark1Mat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(p[0]),
      emissive: new THREE.Color(p[0]),
      emissiveIntensity: 1.2,
    });
    const spark1 = new THREE.Mesh(sparkGeo, spark1Mat);
    orbitGroup.add(spark1);

    const spark2Mat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(p[3]),
      emissive: new THREE.Color(p[3]),
      emissiveIntensity: 1.2,
    });
    const spark2 = new THREE.Mesh(sparkGeo, spark2Mat);
    orbitGroup.add(spark2);

    // ==========================================
    // 7. AMBIENT PARTICLES
    // ==========================================
    const particleCount = 42;
    const partGeo = new THREE.BufferGeometry();
    const partPositions = new Float32Array(particleCount * 3);
    for (let i = 0; i < particleCount; i++) {
      partPositions[i * 3] = (Math.random() - 0.5) * 16;
      partPositions[i * 3 + 1] = (Math.random() - 0.5) * 14;
      partPositions[i * 3 + 2] = (Math.random() - 0.5) * 8 - 1;
    }
    partGeo.setAttribute("position", new THREE.BufferAttribute(partPositions, 3));
    const partMat = new THREE.PointsMaterial({
      color: new THREE.Color(p[0]),
      size: activeTheme.isLight ? 0.35 : 0.5,
      transparent: true,
      opacity: activeTheme.isLight ? 0.4 : 0.7,
      blending: activeTheme.isLight ? THREE.NormalBlending : THREE.AdditiveBlending,
    });
    const particles = new THREE.Points(partGeo, partMat);
    scene.add(particles);

    // ==========================================
    // INTERACTION & ANIMATION LOOP (MOUSE & TOUCH)
    // ==========================================
    let targetRotX = 0;
    let targetRotY = 0;
    let isVisible = true;

    // Viewport IntersectionObserver: Pause rendering when off-screen to save mobile battery
    const visibilityObserver = new IntersectionObserver(
      ([entry]) => {
        isVisible = entry.isIntersecting;
      },
      { threshold: 0.05 }
    );
    visibilityObserver.observe(container);

    // Mouse Interaction
    const onMouseMove = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      const normX = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      const normY = -(((e.clientY - rect.top) / rect.height) * 2 - 1);

      targetRotY = normX * 0.28;
      targetRotX = -normY * 0.28;

      cursorPointLight.position.x = normX * 5;
      cursorPointLight.position.y = normY * 5;
    };

    const onMouseLeave = () => {
      targetRotX = 0;
      targetRotY = 0;
      cursorPointLight.position.set(0, 0, 8);
    };

    // Smartphone Touch Interaction (Fluid thumb tilt)
    const onTouchMove = (e: TouchEvent) => {
      if (e.touches && e.touches.length > 0) {
        const touch = e.touches[0];
        const rect = container.getBoundingClientRect();
        const normX = ((touch.clientX - rect.left) / rect.width) * 2 - 1;
        const normY = -(((touch.clientY - rect.top) / rect.height) * 2 - 1);

        targetRotY = normX * 0.32;
        targetRotX = -normY * 0.32;

        cursorPointLight.position.x = normX * 5;
        cursorPointLight.position.y = normY * 5;
      }
    };

    const onTouchEnd = () => {
      targetRotX = 0;
      targetRotY = 0;
      cursorPointLight.position.set(0, 0, 8);
    };

    container.addEventListener("mousemove", onMouseMove);
    container.addEventListener("mouseleave", onMouseLeave);
    container.addEventListener("touchmove", onTouchMove, { passive: true });
    container.addEventListener("touchend", onTouchEnd, { passive: true });

    const clock = new THREE.Clock();

    const animate = () => {
      animId = requestAnimationFrame(animate);

      // Only perform heavy WebGL render if visible on screen
      if (!isVisible) return;

      const time = clock.getElapsedTime();

      // Smooth GSAP / Lerp parallax
      masterGroup.rotation.y += (targetRotY - masterGroup.rotation.y) * 0.08;
      masterGroup.rotation.x += (targetRotX - masterGroup.rotation.x) * 0.08;

      // Center Group & Exploded Slice floating levitation
      centerGroup.position.y = Math.sin(time * 1.2) * 0.06;
      centerGroup.rotation.z = Math.sin(time * 0.4) * 0.03;
      slice3.position.z = 0.22 + Math.sin(time * 2.0) * 0.06;

      // Widget independent floating levitation
      barWidget.position.y = 2.2 + Math.sin(time * 1.5) * 0.08;
      trendWidget.position.y = 2.1 + Math.sin(time * 1.3 + 1.2) * 0.08;
      dbWidget.position.y = -2.1 + Math.sin(time * 1.6 + 2.4) * 0.08;
      matrixWidget.position.y = -2.1 + Math.sin(time * 1.4 + 3.6) * 0.08;

      // Animate Bar Heights subtly
      for (let i = 0; i < 4; i++) {
        const pulse = 1.0 + Math.sin(time * 2.2 + i * 0.9) * 0.12;
        barMeshes[i].scale.y = pulse;
      }

      // Animate Database Disk rotation
      for (let i = 0; i < 3; i++) {
        dbDisks[i].rotation.y = time * 0.4 * (i % 2 === 0 ? 1 : -1);
      }

      // Animate Matrix Heatmap Cells luminescence
      for (let idx = 0; idx < matrixMats.length; idx++) {
        const intensity = 0.35 + Math.sin(time * 2.5 + idx * 0.45) * 0.25;
        matrixMats[idx].emissiveIntensity = Math.max(0.1, intensity);
      }

      // Orbiting Sparks along tilted ellipses
      const sparkAngle1 = time * 0.8;
      const v1 = new THREE.Vector3(Math.cos(sparkAngle1) * 4.7, Math.sin(sparkAngle1) * 4.7, 0);
      v1.applyEuler(ring1.rotation);
      spark1.position.copy(v1);

      const sparkAngle2 = -time * 0.65 + 1.8;
      const v2 = new THREE.Vector3(Math.cos(sparkAngle2) * 4.3, Math.sin(sparkAngle2) * 4.3, 0);
      v2.applyEuler(ring2.rotation);
      spark2.position.copy(v2);

      // Slow drift of background particles
      particles.rotation.y = time * 0.02;
      particles.rotation.x = Math.sin(time * 0.015) * 0.05;

      renderer.render(scene, camera);
    };

    animate();

    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;

      // Dynamically fit all 3D assets inside mobile smartphones
      const isMob = w < 560;
      const scaleVal = isMob ? Math.min(1.0, Math.max(0.66, w / 510)) : 1.0;
      masterGroup.scale.set(scaleVal, scaleVal, scaleVal);
      camera.position.z = isMob ? 16.5 : 15.0;

      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      container.removeEventListener("mousemove", onMouseMove);
      container.removeEventListener("mouseleave", onMouseLeave);
      container.removeEventListener("touchmove", onTouchMove);
      container.removeEventListener("touchend", onTouchEnd);
      visibilityObserver.disconnect();
      cancelAnimationFrame(animId);

      // Clean up Three.js resources
      scene.traverse((obj) => {
        if (obj instanceof THREE.Mesh) {
          obj.geometry.dispose();
          if (Array.isArray(obj.material)) {
            obj.material.forEach((m) => m.dispose());
          } else if (obj.material) {
            obj.material.dispose();
          }
        }
      });
      renderer.dispose();
    };
  }, [currentTheme]);

  const activeTheme = THEME_PALETTES[currentTheme] || THEME_PALETTES.dark;

  return (
    <div
      ref={containerRef}
      className="relative w-full max-w-[540px] aspect-square max-h-[380px] xs:max-h-[440px] sm:max-h-none flex items-center justify-center select-none"
      style={{ touchAction: "pan-y" }}
    >
      {/* 1. Theme-Reactive Ambient Radial Glow */}
      <div
        className="absolute w-[280px] sm:w-[440px] h-[280px] sm:h-[440px] rounded-full blur-[80px] sm:blur-[130px] pointer-events-none transition-all duration-700 opacity-60 z-0"
        style={{
          background: `radial-gradient(circle, ${activeTheme.bgGlow} 0%, transparent 70%)`,
        }}
      />

      {/* 2. Interactive 3D WebGL Canvas */}
      <canvas
        ref={canvasRef}
        className="relative z-10 w-full h-full cursor-grab active:cursor-grabbing outline-none"
        style={{ background: "transparent", touchAction: "pan-y" }}
      />
    </div>
  );
}
