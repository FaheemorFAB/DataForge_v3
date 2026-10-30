"use client";

import React, { useState, useEffect, useRef } from "react";
import Logo from "./Logo";

interface SplashLoaderProps {
  isLoading: boolean;
  onComplete?: () => void;
}

export default function SplashLoader({ isLoading, onComplete }: SplashLoaderProps) {
  const [shouldRender, setShouldRender] = useState(true);
  const [isFadingOut, setIsFadingOut] = useState(false);
  const mountTime = useRef(Date.now());

  useEffect(() => {
    if (!isLoading) {
      const elapsed = Date.now() - mountTime.current;
      const delay = Math.max(0, 1800 - elapsed);

      const startFadeOut = setTimeout(() => {
        setIsFadingOut(true);
        
        const removeTimeout = setTimeout(() => {
          setShouldRender(false);
          if (onComplete) {
            onComplete();
          }
        }, 450);
      }, delay);
      
      return () => clearTimeout(startFadeOut);
    }
  }, [isLoading, onComplete]);

  if (!shouldRender) return null;

  return (
    <div 
      className={`fixed inset-0 z-[99999] w-screen h-[100dvh] flex flex-col items-center justify-center p-4 transition-opacity duration-500 ease-in-out select-none overscroll-none touch-none ${
        isFadingOut ? 'opacity-0 pointer-events-none' : 'opacity-100'
      }`}
      style={{ background: "var(--bg)" }}
    >
      <div className="flex flex-col items-center justify-center gap-5 sm:gap-6 max-w-xs sm:max-w-sm w-full text-center">
        <div style={{ animation: "twinkle 2.5s ease-in-out infinite" }}>
          <Logo size={40} textSize={22} />
        </div>

        {/* Dynamic Progress indicator */}
        <div className="w-36 sm:w-44 h-1 rounded-full bg-zinc-800/80 overflow-hidden relative border border-white/5 shadow-inner">
          <div 
            className="absolute top-0 bottom-0 left-0 rounded-full"
            style={{
              width: "65%",
              background: "linear-gradient(90deg, #06B6D4, #4F46E5, #ff7043)",
              animation: "pulse 1.6s ease-in-out infinite",
            }}
          />
        </div>

        <span className="text-[10px] sm:text-[11px] font-semibold tracking-widest text-zinc-400 uppercase font-mono">
          Starting Engine...
        </span>
      </div>
    </div>
  );
}
