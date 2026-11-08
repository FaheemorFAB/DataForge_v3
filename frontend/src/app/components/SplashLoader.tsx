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
      <div className="flex flex-col items-center justify-center max-w-xs sm:max-w-sm w-full text-center">
        <div style={{ animation: "twinkle 2.5s ease-in-out infinite" }}>
          <Logo size={42} textSize={24} />
        </div>
      </div>
    </div>
  );
}
