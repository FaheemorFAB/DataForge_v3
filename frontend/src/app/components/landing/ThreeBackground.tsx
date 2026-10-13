"use client";

import React, { useEffect, useRef } from "react";
import * as THREE from "three";

export default function ThreeBackground() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (typeof window === "undefined" || !containerRef.current) return;

    const container = containerRef.current;
    let animationFrameId: number;
    let renderer: THREE.WebGLRenderer | null = null;
    let scene: THREE.Scene | null = null;
    let camera: THREE.PerspectiveCamera | null = null;

    try {
      // Create Scene & Camera
      scene = new THREE.Scene();
      const width = container.clientWidth || window.innerWidth;
      const height = container.clientHeight || window.innerHeight;

      camera = new THREE.PerspectiveCamera(55, width / height, 0.1, 1000);
      camera.position.z = 85;

      // Create WebGL Renderer with alpha transparency
      renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: true,
        powerPreference: "high-performance",
      });
      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.setClearColor(0x000000, 0);

      container.appendChild(renderer.domElement);

      // Check current theme
      const isLightTheme = document.documentElement.getAttribute("data-theme") === "light";
      const primaryHex = isLightTheme ? 0xd946ef : 0xff4310;
      const secondaryHex = isLightTheme ? 0x6366f1 : 0x38bdf8;

      // ── 1. Create Data Constellation Particles ──────────────────────────────
      const particleCount = 1400;
      const particleGeometry = new THREE.BufferGeometry();
      const positions = new Float32Array(particleCount * 3);
      const originalPositions = new Float32Array(particleCount * 3);
      const colors = new Float32Array(particleCount * 3);
      const scales = new Float32Array(particleCount);

      const color1 = new THREE.Color(primaryHex);
      const color2 = new THREE.Color(secondaryHex);
      const colorAccent = new THREE.Color(isLightTheme ? 0xf97316 : 0x818cf8);

      for (let i = 0; i < particleCount; i++) {
        const i3 = i * 3;
        // Wave-like distribution across X, Y, Z
        const x = (Math.random() - 0.5) * 160;
        const y = (Math.random() - 0.5) * 110;
        const z = (Math.random() - 0.5) * 70;

        positions[i3] = x;
        positions[i3 + 1] = y;
        positions[i3 + 2] = z;

        originalPositions[i3] = x;
        originalPositions[i3 + 1] = y;
        originalPositions[i3 + 2] = z;

        // Color gradient interpolation based on position
        const t = (x + 80) / 160;
        const col = Math.random() > 0.4 ? color1.clone().lerp(color2, t) : colorAccent;
        colors[i3] = col.r;
        colors[i3 + 1] = col.g;
        colors[i3 + 2] = col.b;

        scales[i] = Math.random() * 2.2 + 0.8;
      }

      particleGeometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
      particleGeometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));

      // Create smooth circular particle texture
      const canvas = document.createElement("canvas");
      canvas.width = 64;
      canvas.height = 64;
      const ctx = canvas.getContext("2d");
      if (ctx) {
        const grad = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
        grad.addColorStop(0, "rgba(255, 255, 255, 1)");
        grad.addColorStop(0.3, "rgba(255, 255, 255, 0.7)");
        grad.addColorStop(0.7, "rgba(255, 255, 255, 0.15)");
        grad.addColorStop(1, "rgba(255, 255, 255, 0)");
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, 64, 64);
      }
      const particleTexture = new THREE.CanvasTexture(canvas);

      const particleMaterial = new THREE.PointsMaterial({
        size: isLightTheme ? 2.2 : 2.8,
        vertexColors: true,
        transparent: true,
        opacity: isLightTheme ? 0.65 : 0.85,
        map: particleTexture,
        blending: isLightTheme ? THREE.NormalBlending : THREE.AdditiveBlending,
        depthWrite: false,
      });

      const particleSystem = new THREE.Points(particleGeometry, particleMaterial);
      scene.add(particleSystem);

      // ── 2. Create Floating Ethereal Data Nodes & Connecting Grid ────────────
      const gridNodesCount = 60;
      const nodePositions: THREE.Vector3[] = [];
      const nodeGeometry = new THREE.BufferGeometry();
      const nodePositionsArray = new Float32Array(gridNodesCount * 3);

      for (let i = 0; i < gridNodesCount; i++) {
        const v = new THREE.Vector3(
          (Math.random() - 0.5) * 110,
          (Math.random() - 0.5) * 80,
          (Math.random() - 0.5) * 40
        );
        nodePositions.push(v);
        nodePositionsArray[i * 3] = v.x;
        nodePositionsArray[i * 3 + 1] = v.y;
        nodePositionsArray[i * 3 + 2] = v.z;
      }
      nodeGeometry.setAttribute("position", new THREE.BufferAttribute(nodePositionsArray, 3));

      // Geometric line segments connecting nearby nodes
      const linePositions: number[] = [];
      const maxDistance = 24;

      for (let i = 0; i < gridNodesCount; i++) {
        for (let j = i + 1; j < gridNodesCount; j++) {
          const dist = nodePositions[i].distanceTo(nodePositions[j]);
          if (dist < maxDistance) {
            linePositions.push(nodePositions[i].x, nodePositions[i].y, nodePositions[i].z);
            linePositions.push(nodePositions[j].x, nodePositions[j].y, nodePositions[j].z);
          }
        }
      }

      const lineGeometry = new THREE.BufferGeometry();
      lineGeometry.setAttribute("position", new THREE.Float32BufferAttribute(linePositions, 3));

      const lineMaterial = new THREE.LineBasicMaterial({
        color: isLightTheme ? 0x94a3b8 : 0x38bdf8,
        transparent: true,
        opacity: isLightTheme ? 0.18 : 0.22,
        blending: isLightTheme ? THREE.NormalBlending : THREE.AdditiveBlending,
      });

      const lineSegments = new THREE.LineSegments(lineGeometry, lineMaterial);
      scene.add(lineSegments);

      // ── 3. Subtle Floating Wireframe Geometry (Data Crystal) ───────────────
      const crystalGeo = new THREE.IcosahedronGeometry(12, 1);
      const crystalMat = new THREE.MeshBasicMaterial({
        color: isLightTheme ? 0x6366f1 : 0xff4310,
        wireframe: true,
        transparent: true,
        opacity: isLightTheme ? 0.08 : 0.12,
      });
      const crystal = new THREE.Mesh(crystalGeo, crystalMat);
      crystal.position.set(38, 5, -15);
      scene.add(crystal);

      // ── 4. Interactive Mouse Tracking & Parallax ─────────────────────────────
      let mouseX = 0;
      let mouseY = 0;
      let targetX = 0;
      let targetY = 0;

      const handleMouseMove = (event: MouseEvent) => {
        const windowHalfX = window.innerWidth / 2;
        const windowHalfY = window.innerHeight / 2;
        mouseX = (event.clientX - windowHalfX) * 0.0006;
        mouseY = (event.clientY - windowHalfY) * 0.0006;
      };

      window.addEventListener("mousemove", handleMouseMove, { passive: true });

      // ── 5. Resize Handler ───────────────────────────────────────────────────
      const handleResize = () => {
        if (!container || !renderer || !camera) return;
        const w = container.clientWidth || window.innerWidth;
        const h = container.clientHeight || window.innerHeight;
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        renderer.setSize(w, h);
      };

      window.addEventListener("resize", handleResize);

      // ── 6. Animation Loop ───────────────────────────────────────────────────
      const startTime = performance.now();

      const animate = () => {
        animationFrameId = requestAnimationFrame(animate);

        const elapsedTime = (performance.now() - startTime) * 0.001;

        // Smooth camera damping to mouse
        targetX += (mouseX - targetX) * 0.05;
        targetY += (mouseY - targetY) * 0.05;

        if (camera) {
          camera.position.x += (targetX * 24 - camera.position.x) * 0.04;
          camera.position.y += (-targetY * 18 - camera.position.y) * 0.04;
          camera.lookAt(0, 0, 0);
        }

        // Wave motion for particle system
        const posAttr = particleGeometry.attributes.position as THREE.BufferAttribute;
        const posArray = posAttr.array as Float32Array;

        for (let i = 0; i < particleCount; i++) {
          const i3 = i * 3;
          const origX = originalPositions[i3];
          const origY = originalPositions[i3 + 1];

          // Layered sine wave animation
          const wave1 = Math.sin(elapsedTime * 0.6 + origX * 0.04) * 2.5;
          const wave2 = Math.cos(elapsedTime * 0.4 + origY * 0.05) * 2.0;

          posArray[i3 + 2] = originalPositions[i3 + 2] + wave1 + wave2;
        }
        posAttr.needsUpdate = true;

        // Subtle continuous rotation
        particleSystem.rotation.y = elapsedTime * 0.025;
        particleSystem.rotation.x = Math.sin(elapsedTime * 0.015) * 0.08;

        lineSegments.rotation.y = elapsedTime * 0.018;
        lineSegments.rotation.z = Math.cos(elapsedTime * 0.02) * 0.05;

        crystal.rotation.x = elapsedTime * 0.08;
        crystal.rotation.y = elapsedTime * 0.12;

        if (renderer && scene && camera) {
          renderer.render(scene, camera);
        }
      };

      animate();

      // ── 7. Theme Observer ───────────────────────────────────────────────────
      const observer = new MutationObserver(() => {
        const isLight = document.documentElement.getAttribute("data-theme") === "light";
        if (particleMaterial && crystalMat && lineMaterial) {
          particleMaterial.opacity = isLight ? 0.65 : 0.85;
          particleMaterial.blending = isLight ? THREE.NormalBlending : THREE.AdditiveBlending;
          crystalMat.opacity = isLight ? 0.08 : 0.12;
          lineMaterial.opacity = isLight ? 0.18 : 0.22;
          lineMaterial.blending = isLight ? THREE.NormalBlending : THREE.AdditiveBlending;
        }
      });
      observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

      // ── 8. Cleanup ─────────────────────────────────────────────────────────
      return () => {
        cancelAnimationFrame(animationFrameId);
        window.removeEventListener("mousemove", handleMouseMove);
        window.removeEventListener("resize", handleResize);
        observer.disconnect();

        if (renderer) {
          renderer.dispose();
          if (renderer.domElement && renderer.domElement.parentNode) {
            renderer.domElement.parentNode.removeChild(renderer.domElement.parentNode === container ? renderer.domElement : renderer.domElement);
          }
        }
        particleGeometry.dispose();
        particleMaterial.dispose();
        particleTexture.dispose();
        nodeGeometry.dispose();
        lineGeometry.dispose();
        lineMaterial.dispose();
        crystalGeo.dispose();
        crystalMat.dispose();
      };
    } catch (err) {
      console.warn("ThreeBackground WebGL init fallback:", err);
    }
  }, []);

  return (
    <div
      ref={containerRef}
      className="absolute inset-0 pointer-events-none overflow-hidden z-0"
      style={{
        maskImage: "radial-gradient(ellipse at center, rgba(0,0,0,1) 40%, rgba(0,0,0,0) 80%)",
        WebkitMaskImage: "radial-gradient(ellipse at center, rgba(0,0,0,1) 40%, rgba(0,0,0,0) 80%)",
      }}
    />
  );
}
