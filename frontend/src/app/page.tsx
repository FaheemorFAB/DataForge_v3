"use client";

import React, { useState, useEffect } from "react";
import LoginModal from "./components/landing/LoginModal";
import Header from "./components/landing/Header";
import HeroSection from "./components/landing/HeroSection";
import FeatureGrid from "./components/landing/FeatureGrid";
import StatsStrip from "./components/landing/StatsStrip";
import BuiltFor from "./components/landing/BuiltFor";
import FAQ from "./components/landing/FAQ";
import CTABanner from "./components/landing/CTABanner";
import Footer from "./components/landing/Footer";
import ProcessTimeline from "./components/landing/ProcessTimeline";
import TeamSection from "./components/landing/TeamSection";

export default function Home() {
  const [showLoginModal, setShowLoginModal] = useState(false);

  useEffect(() => {
    // Check query string for login modal
    if (typeof window !== "undefined") {
      if (new URLSearchParams(window.location.search).get('login') === '1') {
        setShowLoginModal(true);
        window.history.replaceState({}, '', '/');
      }
    }
  }, []);

  return (
    <>
      <div className="noise"></div>
      <div className="mesh"></div>

      {showLoginModal && (
        <LoginModal onClose={() => setShowLoginModal(false)} />
      )}

      <Header onLoginClick={() => setShowLoginModal(true)} />

      <main className="flex-grow flex flex-col items-center justify-center py-4 md:py-6 w-full max-w-7xl mx-auto">
        <HeroSection onLoginRequired={() => setShowLoginModal(true)} />
      </main>

      <ProcessTimeline />

      <FeatureGrid />

      <StatsStrip />

      <BuiltFor />

      <CTABanner />

      <TeamSection />

      <FAQ />

      <Footer />
    </>
  );
}
