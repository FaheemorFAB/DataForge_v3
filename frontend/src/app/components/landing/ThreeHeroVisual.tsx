"use client";

import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import gsap from "gsap";

export default function ThreeHeroVisual() {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [themeMode, setThemeMode] = useState<"light" | "dark">("dark");

  useEffect(() => {
    // Detect theme from html element
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

  useEffect(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;

    let animationFrameId: number;
    let renderer: THREE.WebGLRenderer;
    let scene: THREE.Scene;
    let camera: THREE.PerspectiveCamera;

    const width = container.clientWidth || 550;
    const height = container.clientHeight || 520;
    const isLight = themeMode === "light";

    // 1. Scene & Camera Setup
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 100);
    camera.position.set(0, 0, 7.8);

    try {
      renderer = new THREE.WebGLRenderer({
        canvas,
        alpha: true,
        antialias: true,
        powerPreference: "high-performance",
      });
      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = isLight ? 1.05 : 1.25;
    } catch (e) {
      console.warn("Three.js WebGL fallback:", e);
      return;
    }

    // 2. Lights
    const ambientLight = new THREE.AmbientLight(
      isLight ? 0xffffff : 0xdbeafe,
      isLight ? 1.4 : 1.1
    );
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(
      isLight ? 0xffffff : 0x38bdf8,
      isLight ? 1.8 : 2.4
    );
    dirLight1.position.set(5, 8, 6);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(
      isLight ? 0xf43f5e : 0xf43f5e,
      isLight ? 1.0 : 1.6
    );
    dirLight2.position.set(-6, -4, 4);
    scene.add(dirLight2);

    const pointLight = new THREE.PointLight(
      isLight ? 0x0284c7 : 0x00f0ff,
      isLight ? 1.5 : 2.5,
      12
    );
    pointLight.position.set(0, 1, 3);
    scene.add(pointLight);

    // Root cluster group
    const rootGroup = new THREE.Group();
    // Default isometric tilt
    rootGroup.rotation.x = 0.38;
    rootGroup.rotation.y = -0.32;
    scene.add(rootGroup);

    // Helper: Rounded Rectangle Tile Shape
    function createRoundedTileGeo(w: number, h: number, r: number, d: number) {
      const shape = new THREE.Shape();
      const x = -w / 2;
      const y = -h / 2;
      shape.moveTo(x + r, y);
      shape.lineTo(x + w - r, y);
      shape.quadraticCurveTo(x + w, y, x + w, y + r);
      shape.lineTo(x + w, y + h - r);
      shape.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
      shape.lineTo(x + r, y + h);
      shape.quadraticCurveTo(x, y + h, x, y + h - r);
      shape.lineTo(x, y + r);
      shape.quadraticCurveTo(x, y, x + r, y);

      return new THREE.ExtrudeGeometry(shape, {
        depth: d,
        bevelEnabled: true,
        bevelSegments: 4,
        steps: 1,
        bevelSize: 0.02,
        bevelThickness: 0.02,
      });
    }

    // Glass Material Factory
    const getGlassMat = (glowColor: number) =>
      new THREE.MeshPhysicalMaterial({
        color: isLight ? 0xffffff : 0x1e293b,
        metalness: 0.1,
        roughness: isLight ? 0.15 : 0.25,
        transmission: isLight ? 0.8 : 0.65,
        thickness: 0.5,
        transparent: true,
        opacity: isLight ? 0.85 : 0.7,
        emissive: new THREE.Color(glowColor),
        emissiveIntensity: isLight ? 0.05 : 0.25,
        reflectivity: 0.9,
      });

    // ════════════════════════════════════════════════════════════
    // 1. CENTER PIE CHART ON GLASS PEDESTAL
    // ════════════════════════════════════════════════════════════
    const centerGroup = new THREE.Group();
    rootGroup.add(centerGroup);

    // Glass Pedestal for Pie Chart
    const pedestalGeo = createRoundedTileGeo(2.4, 2.4, 0.35, 0.06);
    const pedestalMat = getGlassMat(isLight ? 0xbae6fd : 0x0284c7);
    const pedestal = new THREE.Mesh(pedestalGeo, pedestalMat);
    pedestal.position.z = -0.15;
    centerGroup.add(pedestal);

    // Glowing rim for pedestal
    const pedestalEdgeGeo = new THREE.EdgesGeometry(pedestalGeo);
    const pedestalEdgeMat = new THREE.LineBasicMaterial({
      color: isLight ? 0x0284c7 : 0x38bdf8,
      transparent: true,
      opacity: isLight ? 0.5 : 0.8,
    });
    const pedestalEdges = new THREE.LineSegments(pedestalEdgeGeo, pedestalEdgeMat);
    pedestalEdges.position.z = -0.15;
    centerGroup.add(pedestalEdges);

    // Function to generate pie wedges
    function createPieWedge(
      radius: number,
      startAngle: number,
      endAngle: number,
      depth: number,
      color: number,
      isExploded = false
    ) {
      const shape = new THREE.Shape();
      shape.moveTo(0, 0);
      shape.arc(0, 0, radius, startAngle, endAngle, false);
      shape.lineTo(0, 0);

      const geo = new THREE.ExtrudeGeometry(shape, {
        depth,
        bevelEnabled: true,
        bevelSegments: 4,
        steps: 1,
        bevelSize: 0.02,
        bevelThickness: 0.02,
      });

      const mat = new THREE.MeshPhysicalMaterial({
        color,
        roughness: 0.2,
        metalness: 0.2,
        clearcoat: 0.8,
        clearcoatRoughness: 0.1,
        emissive: new THREE.Color(color),
        emissiveIntensity: isLight ? 0.08 : 0.28,
      });

      const mesh = new THREE.Mesh(geo, mat);

      if (isExploded) {
        const midAngle = (startAngle + endAngle) / 2;
        mesh.position.x = Math.cos(midAngle) * 0.24;
        mesh.position.y = Math.sin(midAngle) * 0.24;
        mesh.position.z = 0.05;
      }

      return mesh;
    }

    const pieRadius = 0.82;
    const pieDepth = 0.28;

    // Slices matching user concept image:
    // Cyan (main), Magenta/Pink (exploded slice), Gold/Amber, Violet/Purple, Emerald
    const slice1 = createPieWedge(pieRadius, 0, Math.PI * 0.95, pieDepth, isLight ? 0x0284c7 : 0x00f0ff);
    const slice2 = createPieWedge(pieRadius, Math.PI * 0.95, Math.PI * 1.35, pieDepth, 0xf43f5e, true); // Exploded
    const slice3 = createPieWedge(pieRadius, Math.PI * 1.35, Math.PI * 1.65, pieDepth, 0xf59e0b);
    const slice4 = createPieWedge(pieRadius, Math.PI * 1.65, Math.PI * 1.9, pieDepth, 0x8b5cf6);
    const slice5 = createPieWedge(pieRadius, Math.PI * 1.9, Math.PI * 2, pieDepth, 0x10b981);

    const pieSlices = new THREE.Group();
    pieSlices.add(slice1, slice2, slice3, slice4, slice5);
    centerGroup.add(pieSlices);

    // ════════════════════════════════════════════════════════════
    // 2. TOP-LEFT TILE: 3D BAR CHART
    // ════════════════════════════════════════════════════════════
    const barTileGroup = new THREE.Group();
    barTileGroup.position.set(-2.0, 1.4, 0.4);
    rootGroup.add(barTileGroup);

    const barTileBase = new THREE.Mesh(
      createRoundedTileGeo(1.3, 1.3, 0.2, 0.04),
      getGlassMat(isLight ? 0x38bdf8 : 0x0284c7)
    );
    barTileGroup.add(barTileBase);

    // 4 vertical bars
    const barHeights = [0.25, 0.5, 0.75, 0.4];
    const barColors = [0x00f0ff, 0xa855f7, 0xf43f5e, 0x38bdf8];
    const barSpacing = 0.25;
    const startX = -((barHeights.length - 1) * barSpacing) / 2;

    barHeights.forEach((h, i) => {
      const barGeo = new THREE.CylinderGeometry(0.07, 0.07, h, 16);
      const barMat = new THREE.MeshStandardMaterial({
        color: barColors[i],
        roughness: 0.2,
        metalness: 0.3,
        emissive: new THREE.Color(barColors[i]),
        emissiveIntensity: isLight ? 0.15 : 0.4,
      });
      const bar = new THREE.Mesh(barGeo, barMat);
      bar.position.set(startX + i * barSpacing, -0.4 + h / 2, 0.08);
      barTileGroup.add(bar);
    });

    // ════════════════════════════════════════════════════════════
    // 3. TOP-RIGHT TILE: 3D LINE / TREND WAVE
    // ════════════════════════════════════════════════════════════
    const lineTileGroup = new THREE.Group();
    lineTileGroup.position.set(1.9, 1.5, 0.3);
    rootGroup.add(lineTileGroup);

    const lineTileBase = new THREE.Mesh(
      createRoundedTileGeo(1.3, 1.3, 0.2, 0.04),
      getGlassMat(isLight ? 0xf43f5e : 0xd946ef)
    );
    lineTileGroup.add(lineTileBase);

    // 3D Curve
    const linePoints = [
      new THREE.Vector3(-0.45, -0.3, 0.08),
      new THREE.Vector3(-0.15, 0.05, 0.08),
      new THREE.Vector3(0.1, -0.1, 0.08),
      new THREE.Vector3(0.42, 0.32, 0.08),
    ];
    const lineCurve = new THREE.CatmullRomCurve3(linePoints);
    const lineGeo = new THREE.TubeGeometry(lineCurve, 24, 0.035, 8, false);
    const lineMat = new THREE.MeshStandardMaterial({
      color: 0x00f0ff,
      emissive: 0x00f0ff,
      emissiveIntensity: isLight ? 0.4 : 0.8,
      roughness: 0.2,
    });
    lineTileGroup.add(new THREE.Mesh(lineGeo, lineMat));

    // Data points on the line
    linePoints.forEach((pt) => {
      const dotGeo = new THREE.SphereGeometry(0.065, 16, 16);
      const dotMat = new THREE.MeshStandardMaterial({
        color: 0xf43f5e,
        emissive: 0xf43f5e,
        emissiveIntensity: 0.6,
      });
      const dot = new THREE.Mesh(dotGeo, dotMat);
      dot.position.copy(pt);
      lineTileGroup.add(dot);
    });

    // ════════════════════════════════════════════════════════════
    // 4. BOTTOM-LEFT TILE: 3D DATABASE STORAGE
    // ════════════════════════════════════════════════════════════
    const dbTileGroup = new THREE.Group();
    dbTileGroup.position.set(-1.8, -1.3, 0.5);
    rootGroup.add(dbTileGroup);

    const dbTileBase = new THREE.Mesh(
      createRoundedTileGeo(1.3, 1.3, 0.2, 0.04),
      getGlassMat(isLight ? 0xf59e0b : 0xeab308)
    );
    dbTileGroup.add(dbTileBase);

    // Stacked database cylinders
    const diskCount = 3;
    const diskRadius = 0.32;
    const diskHeight = 0.12;
    const diskGap = 0.06;

    for (let i = 0; i < diskCount; i++) {
      const diskGeo = new THREE.CylinderGeometry(diskRadius, diskRadius, diskHeight, 32);
      const diskMat = new THREE.MeshStandardMaterial({
        color: isLight ? 0x0284c7 : 0x38bdf8,
        metalness: 0.4,
        roughness: 0.2,
        emissive: new THREE.Color(i === 1 ? 0xf59e0b : 0x00f0ff),
        emissiveIntensity: isLight ? 0.15 : 0.3,
      });
      const disk = new THREE.Mesh(diskGeo, diskMat);
      disk.position.set(0, -0.22 + i * (diskHeight + diskGap), 0.1);
      dbTileGroup.add(disk);

      // Glowing LED torus ring between layers
      const torusGeo = new THREE.TorusGeometry(diskRadius + 0.015, 0.015, 8, 32);
      const torusMat = new THREE.MeshBasicMaterial({
        color: i === 1 ? 0xf59e0b : 0x00f0ff,
      });
      const torus = new THREE.Mesh(torusGeo, torusMat);
      torus.rotation.x = Math.PI / 2;
      torus.position.copy(disk.position);
      dbTileGroup.add(torus);
    }

    // ════════════════════════════════════════════════════════════
    // 5. BOTTOM-RIGHT TILE: 3D PIPELINE / DAG NODES
    // ════════════════════════════════════════════════════════════
    const dagTileGroup = new THREE.Group();
    dagTileGroup.position.set(1.9, -1.2, 0.4);
    rootGroup.add(dagTileGroup);

    const dagTileBase = new THREE.Mesh(
      createRoundedTileGeo(1.3, 1.3, 0.2, 0.04),
      getGlassMat(isLight ? 0x10b981 : 0x059669)
    );
    dagTileGroup.add(dagTileBase);

    // Root input node
    const inNodeGeo = new THREE.SphereGeometry(0.12, 20, 20);
    const inNodeMat = new THREE.MeshStandardMaterial({
      color: 0x38bdf8,
      emissive: 0x38bdf8,
      emissiveIntensity: 0.5,
      roughness: 0.2,
    });
    const inNode = new THREE.Mesh(inNodeGeo, inNodeMat);
    inNode.position.set(-0.35, 0, 0.12);
    dagTileGroup.add(inNode);

    // Two branched output nodes
    const outNode1 = new THREE.Mesh(
      new THREE.SphereGeometry(0.1, 16, 16),
      new THREE.MeshStandardMaterial({ color: 0x10b981, emissive: 0x10b981, emissiveIntensity: 0.6 })
    );
    outNode1.position.set(0.35, 0.25, 0.12);
    dagTileGroup.add(outNode1);

    const outNode2 = new THREE.Mesh(
      new THREE.SphereGeometry(0.1, 16, 16),
      new THREE.MeshStandardMaterial({ color: 0xf43f5e, emissive: 0xf43f5e, emissiveIntensity: 0.6 })
    );
    outNode2.position.set(0.35, -0.25, 0.12);
    dagTileGroup.add(outNode2);

    // Branching connecting tubes
    const branchCurve1 = new THREE.CubicBezierCurve3(
      inNode.position,
      new THREE.Vector3(-0.05, 0.05, 0.12),
      new THREE.Vector3(0.1, 0.25, 0.12),
      outNode1.position
    );
    const branchCurve2 = new THREE.CubicBezierCurve3(
      inNode.position,
      new THREE.Vector3(-0.05, -0.05, 0.12),
      new THREE.Vector3(0.1, -0.25, 0.12),
      outNode2.position
    );

    const tubeGeo1 = new THREE.TubeGeometry(branchCurve1, 20, 0.025, 8, false);
    const tubeGeo2 = new THREE.TubeGeometry(branchCurve2, 20, 0.025, 8, false);
    const tubeMat = new THREE.MeshStandardMaterial({
      color: 0x00f0ff,
      emissive: 0x00f0ff,
      emissiveIntensity: 0.4,
    });
    dagTileGroup.add(new THREE.Mesh(tubeGeo1, tubeMat));
    dagTileGroup.add(new THREE.Mesh(tubeGeo2, tubeMat));

    // ════════════════════════════════════════════════════════════
    // 6. 3D ORBITAL ELLIPTICAL RINGS & PARTICLES
    // ════════════════════════════════════════════════════════════
    const orbitGroup = new THREE.Group();
    rootGroup.add(orbitGroup);

    const orbit1Curve = new THREE.EllipseCurve(0, 0, 3.1, 1.8, 0, 2 * Math.PI, false, 0);
    const orbit1Pts = orbit1Curve.getPoints(120);
    const orbit1Geo = new THREE.BufferGeometry().setFromPoints(
      orbit1Pts.map((p) => new THREE.Vector3(p.x, p.y, 0))
    );
    const orbit1Mat = new THREE.LineBasicMaterial({
      color: isLight ? 0x0284c7 : 0x38bdf8,
      transparent: true,
      opacity: isLight ? 0.35 : 0.6,
    });
    const orbit1 = new THREE.Line(orbit1Geo, orbit1Mat);
    orbit1.rotation.x = Math.PI / 3.4;
    orbit1.rotation.y = -Math.PI / 12;
    orbitGroup.add(orbit1);

    const orbit2Curve = new THREE.EllipseCurve(0, 0, 3.3, 2.0, 0, 2 * Math.PI, false, 0);
    const orbit2Pts = orbit2Curve.getPoints(120);
    const orbit2Geo = new THREE.BufferGeometry().setFromPoints(
      orbit2Pts.map((p) => new THREE.Vector3(p.x, p.y, 0))
    );
    const orbit2Mat = new THREE.LineBasicMaterial({
      color: isLight ? 0xf43f5e : 0xec4899,
      transparent: true,
      opacity: isLight ? 0.28 : 0.45,
    });
    const orbit2 = new THREE.Line(orbit2Geo, orbit2Mat);
    orbit2.rotation.x = Math.PI / 2.8;
    orbit2.rotation.y = Math.PI / 8;
    orbitGroup.add(orbit2);

    // Glowing spark particles traveling on the orbit
    const particleCount = 28;
    const particleGeo = new THREE.BufferGeometry();
    const particlePositions = new Float32Array(particleCount * 3);
    for (let i = 0; i < particleCount; i++) {
      const t = i / particleCount;
      const pt = orbit1Curve.getPoint(t);
      particlePositions[i * 3] = pt.x;
      particlePositions[i * 3 + 1] = pt.y;
      particlePositions[i * 3 + 2] = 0;
    }
    particleGeo.setAttribute("position", new THREE.BufferAttribute(particlePositions, 3));
    const particleMat = new THREE.PointsMaterial({
      color: isLight ? 0x0284c7 : 0x00f0ff,
      size: 0.08,
      transparent: true,
      opacity: isLight ? 0.7 : 0.9,
    });
    const orbitParticles = new THREE.Points(particleGeo, particleMat);
    orbit1.add(orbitParticles);

    // ════════════════════════════════════════════════════════════
    // 7. GSAP MOUSE PARALLAX & CONTINUOUS FLOATING ANIMATIONS
    // ════════════════════════════════════════════════════════════
    const mouse = { x: 0, y: 0 };
    const handleMouseMove = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      const normX = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      const normY = -(((e.clientY - rect.top) / rect.height) * 2 - 1);
      mouse.x = normX;
      mouse.y = normY;

      // GSAP smooth scene tilt
      gsap.to(rootGroup.rotation, {
        x: 0.38 - mouse.y * 0.25,
        y: -0.32 + mouse.x * 0.35,
        duration: 1.2,
        ease: "power2.out",
        overwrite: "auto",
      });

      // Individual parallax on satellite tiles
      gsap.to(barTileGroup.position, {
        z: 0.4 + mouse.y * 0.2,
        duration: 1.0,
        ease: "power2.out",
      });
      gsap.to(lineTileGroup.position, {
        z: 0.3 - mouse.x * 0.2,
        duration: 1.0,
        ease: "power2.out",
      });
      gsap.to(dbTileGroup.position, {
        z: 0.5 - mouse.y * 0.2,
        duration: 1.0,
        ease: "power2.out",
      });
      gsap.to(dagTileGroup.position, {
        z: 0.4 + mouse.x * 0.2,
        duration: 1.0,
        ease: "power2.out",
      });
    };

    window.addEventListener("mousemove", handleMouseMove);

    // Continuous Render Loop
    let clock = new THREE.Clock();
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      // Gentle floating physics for each tile (sine wave offset)
      centerGroup.position.z = Math.sin(elapsedTime * 1.5) * 0.08;
      barTileGroup.position.y = 1.4 + Math.sin(elapsedTime * 1.8 + 0.5) * 0.06;
      lineTileGroup.position.y = 1.5 + Math.sin(elapsedTime * 1.6 + 1.2) * 0.06;
      dbTileGroup.position.y = -1.3 + Math.sin(elapsedTime * 1.7 + 2.1) * 0.06;
      dagTileGroup.position.y = -1.2 + Math.sin(elapsedTime * 1.9 + 3.0) * 0.06;

      // Slow orbital rotation
      orbit1.rotation.z = elapsedTime * 0.08;
      orbit2.rotation.z = -elapsedTime * 0.06;

      // Rotate central pie slightly
      pieSlices.rotation.z = Math.sin(elapsedTime * 0.4) * 0.1;

      renderer.render(scene, camera);
    };

    animate();

    // Resize Handler
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
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("resize", handleResize);
      cancelAnimationFrame(animationFrameId);
      renderer.dispose();
    };
  }, [themeMode]);

  const isLight = themeMode === "light";

  return (
    <div
      ref={containerRef}
      className="relative w-full h-[480px] sm:h-[540px] lg:h-[600px] flex items-center justify-center select-none"
    >
      {/* Three.js Canvas */}
      <canvas
        ref={canvasRef}
        className="w-full h-full cursor-grab active:cursor-grabbing block"
      />

      {/* Floating 3D Badge Pills around the Orbit (Strict Rule: Dark text over light colors) */}
      <div className="absolute inset-0 pointer-events-none flex flex-col justify-between p-4 sm:p-6">
        {/* Top: Ingest */}
        <div className="flex justify-center">
          <div
            className={`px-3.5 py-1.5 rounded-full text-xs font-black tracking-wide border shadow-xl backdrop-blur-md transition-all duration-300 animate-pulse ${
              isLight
                ? "bg-white/90 text-slate-900 border-slate-300 shadow-slate-300/40"
                : "bg-slate-900/80 text-cyan-400 border-cyan-500/40 shadow-cyan-500/20"
            }`}
          >
            ✦ Ingest
          </div>
        </div>

        {/* Middle row: Structure (left) & Predict (right) */}
        <div className="flex justify-between items-center w-full px-2 sm:px-6">
          <div
            className={`px-3.5 py-1.5 rounded-full text-xs font-black tracking-wide border shadow-xl backdrop-blur-md transition-all duration-300 ${
              isLight
                ? "bg-white/90 text-slate-900 border-slate-300 shadow-slate-300/40"
                : "bg-slate-900/80 text-purple-300 border-purple-500/40 shadow-purple-500/20"
            }`}
          >
            ✦ Structure
          </div>

          <div
            className={`px-3.5 py-1.5 rounded-full text-xs font-black tracking-wide border shadow-xl backdrop-blur-md transition-all duration-300 ${
              isLight
                ? "bg-white/90 text-slate-900 border-slate-300 shadow-slate-300/40"
                : "bg-slate-900/80 text-pink-400 border-pink-500/40 shadow-pink-500/20"
            }`}
          >
            ✦ Predict
          </div>
        </div>

        {/* Bottom: Insight */}
        <div className="flex justify-center">
          <div
            className={`px-3.5 py-1.5 rounded-full text-xs font-black tracking-wide border shadow-xl backdrop-blur-md transition-all duration-300 ${
              isLight
                ? "bg-white/90 text-slate-900 border-slate-300 shadow-slate-300/40"
                : "bg-slate-900/80 text-emerald-400 border-emerald-500/40 shadow-emerald-500/20"
            }`}
          >
            ✦ Insight
          </div>
        </div>
      </div>
    </div>
  );
}
