"use client";

import React, { useEffect, useState, useRef } from "react";

const THEMES = [
  'dark', 'light', 'dracula', 'slate', 'emerald', 'nord', 'luxury', 'cupcake', 'solarized', 'lavender', 'matcha'
];

const FONTS = [
  { id: 'inter', name: 'Inter' },
  { id: 'outfit', name: 'Outfit' },
  { id: 'poppins', name: 'Poppins' },
  { id: 'roboto-mono', name: 'Roboto Mono' },
  { id: 'playfair', name: 'Playfair Display' },
  { id: 'rajdhani', name: 'Rajdhani' }
];

export default function ThemeSwitcher() {
  const [currentTheme, setCurrentTheme] = useState('light');
  const [currentFont, setCurrentFont] = useState('inter');
  const [activeTab, setActiveTab] = useState<'themes' | 'fonts'>('themes');
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const savedTheme = localStorage.getItem('analyst-theme') || 'light';
    const savedFont = localStorage.getItem('analyst-font') || 'inter';
    setCurrentTheme(savedTheme);
    setCurrentFont(savedFont);
    document.documentElement.setAttribute('data-theme', savedTheme);
    document.documentElement.setAttribute('data-font', savedFont);
  }, []);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const setTheme = (t: string) => {
    setCurrentTheme(t);
    localStorage.setItem('analyst-theme', t);
    document.documentElement.setAttribute('data-theme', t);
    const f = document.getElementById('eda-frame') as HTMLIFrameElement;
    if (f && f.contentWindow) {
      f.contentWindow.postMessage({type:'THEME_CHANGED', theme: t}, '*');
    }
  };

  const setFont = (f: string) => {
    setCurrentFont(f);
    localStorage.setItem('analyst-font', f);
    document.documentElement.setAttribute('data-font', f);
  };

  return (
    <div className="relative z-[9999]" ref={dropdownRef}>
      <button onClick={() => setIsOpen(!isOpen)} className="ibt mr-1" aria-label="Toggle Theme">
        {/* Keeping original icon as requested */}
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 14.7255 3.09032 17.1962 4.85857 19C5.32626 19.4754 5.99264 19.7423 6.66667 19.7423C7.03967 19.7423 7.39893 19.8659 7.69348 20.0954L8.13488 20.4393C8.94828 21.0719 9.94589 21.4925 11.0028 21.7857C11.3323 21.877 11.666 21.9489 12 22Z" />
          <circle cx="7.5" cy="10.5" r="1.2" fill="currentColor" stroke="none" />
          <circle cx="11.5" cy="7.5" r="1.2" fill="currentColor" stroke="none" />
          <circle cx="16.5" cy="9.5" r="1.2" fill="currentColor" stroke="none" />
          <circle cx="14.5" cy="14.5" r="1.2" fill="currentColor" stroke="none" />
        </svg>
      </button>
      
      {isOpen && (
        <div 
          className="absolute right-0 rounded-xl top-full max-h-96 w-64 overflow-hidden shadow-2xl mt-2 border flex flex-col z-[10000]"
          style={{ background: "var(--card)", color: "var(--txt)", borderColor: "var(--border)" }}
        >
        
        {/* Toggle Tabs */}
        <div className="flex gap-1.5 p-1 mx-3 mt-3 mb-1 shrink-0 rounded-lg" style={{ background: "var(--border)" }}>
          <button 
            className={`flex-1 text-[11px] font-bold py-1.5 rounded-md transition-all duration-300 ${activeTab === 'themes' ? 'shadow-sm' : 'hover:opacity-80'}`}
            style={activeTab === 'themes'
              ? { background: 'var(--accent)', color: '#fff' }
              : { background: 'transparent', color: 'var(--txt-m)' }}
            onClick={(e) => { e.preventDefault(); setActiveTab('themes'); }}
          >
            THEMES
          </button>
          <button 
            className={`flex-1 text-[11px] font-bold py-1.5 rounded-md transition-all duration-300 ${activeTab === 'fonts' ? 'shadow-sm' : 'hover:opacity-80'}`}
            style={activeTab === 'fonts'
              ? { background: 'var(--accent)', color: '#fff' }
              : { background: 'transparent', color: 'var(--txt-m)' }}
            onClick={(e) => { e.preventDefault(); setActiveTab('fonts'); }}
          >
            TYPOGRAPHY
          </button>
        </div>

        {/* Content Area */}
        <div className="p-3 overflow-y-auto flex-1 custom-scrollbar">
          
          {/* Themes Section */}
          {activeTab === 'themes' && (
            <div className="grid grid-cols-1 gap-1.5">
              {THEMES.map((theme) => (
                <button
                  key={theme}
                  className="overflow-hidden rounded-lg text-left border transition-all"
                  style={{
                    borderColor: currentTheme === theme ? 'var(--accent)' : 'var(--border)',
                    background: currentTheme === theme ? 'var(--hover)' : 'transparent',
                  }}
                  onClick={() => setTheme(theme)}
                >
                  <div className="flex items-center gap-3 px-3 py-2.5">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      width="12"
                      height="12"
                      viewBox="0 0 24 24"
                      fill="currentColor"
                      style={{ color: "var(--accent)" }}
                      className={`shrink-0 ${currentTheme === theme ? '' : 'invisible'}`}
                    >
                      <path d="M20.285 2l-11.285 11.567-5.286-5.011-3.714 3.716 9 8.728 15-15.285z" />
                    </svg>
                    <span className="flex-grow text-[12px] capitalize font-bold" style={{ textAlign: "left", color: "var(--txt)" }}>{theme}</span>
                    <div className="flex h-full shrink-0 flex-wrap gap-1">
                      <div className="w-2 h-3 rounded-full" style={{ background: "var(--accent)" }}></div>
                      <div className="w-2 h-3 rounded-full" style={{ background: "var(--txt-m)" }}></div>
                      <div className="w-2 h-3 rounded-full" style={{ background: "var(--border)" }}></div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}

          {/* Fonts Section */}
          {activeTab === 'fonts' && (
            <div className="grid grid-cols-1 gap-1">
              {FONTS.map((font) => (
                <button
                  key={font.id}
                  onClick={() => setFont(font.id)}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors border"
                  style={{
                    background: currentFont === font.id ? 'var(--hover)' : 'transparent',
                    color: currentFont === font.id ? 'var(--accent)' : 'var(--txt)',
                    borderColor: currentFont === font.id ? 'var(--accent)' : 'transparent',
                  }}
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="12"
                    height="12"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                    style={{ color: "var(--accent)" }}
                    className={`shrink-0 ${currentFont === font.id ? '' : 'invisible'}`}
                  >
                    <path d="M20.285 2l-11.285 11.567-5.286-5.011-3.714 3.716 9 8.728 15-15.285z" />
                  </svg>
                  <span className="text-[13px] font-bold" style={{ fontFamily: `var(--font-${font.id}, ${font.name})` }}>{font.name}</span>
                </button>
              ))}
            </div>
          )}
          
        </div>
      </div>
      )}
    </div>
  );
}
