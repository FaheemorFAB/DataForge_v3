"use client";

import React, { useEffect, useState } from "react";

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

  useEffect(() => {
    const savedTheme = localStorage.getItem('analyst-theme') || 'light';
    const savedFont = localStorage.getItem('analyst-font') || 'inter';
    setCurrentTheme(savedTheme);
    setCurrentFont(savedFont);
    document.documentElement.setAttribute('data-theme', savedTheme);
    document.documentElement.setAttribute('data-font', savedFont);
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
    <div className="dropdown dropdown-end z-[9999]">
      <div tabIndex={0} role="button" className="ibt mr-1">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 14.7255 3.09032 17.1962 4.85857 19C5.32626 19.4754 5.99264 19.7423 6.66667 19.7423C7.03967 19.7423 7.39893 19.8659 7.69348 20.0954L8.13488 20.4393C8.94828 21.0719 9.94589 21.4925 11.0028 21.7857C11.3323 21.877 11.666 21.9489 12 22Z" />
          <circle cx="7.5" cy="10.5" r="1.2" fill="currentColor" stroke="none" />
          <circle cx="11.5" cy="7.5" r="1.2" fill="currentColor" stroke="none" />
          <circle cx="16.5" cy="9.5" r="1.2" fill="currentColor" stroke="none" />
          <circle cx="14.5" cy="14.5" r="1.2" fill="currentColor" stroke="none" />
        </svg>
      </div>
      <div tabIndex={0} className="dropdown-content bg-base-200 text-base-content rounded-box top-px max-h-96 w-60 overflow-y-auto shadow-2xl mt-12 border border-base-300">
        
        {/* Themes Section */}
        <div className="p-3">
          <h4 className="text-[10px] font-black uppercase tracking-widest text-base-content/50 mb-2 px-1 text-left">Themes</h4>
          <div className="grid grid-cols-1 gap-1.5">
            {THEMES.map((theme) => (
              <button
                key={theme}
                className="outline-base-content overflow-hidden rounded-lg text-left"
                onClick={() => setTheme(theme)}
              >
                <div
                  data-theme={theme}
                  className="bg-base-100 text-base-content w-full cursor-pointer font-sans transition-all hover:brightness-110"
                >
                  <div className="flex items-center gap-3 px-3 py-2.5">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      width="12"
                      height="12"
                      viewBox="0 0 24 24"
                      fill="currentColor"
                      className={`shrink-0 ${currentTheme === theme ? '' : 'invisible'}`}
                    >
                      <path d="M20.285 2l-11.285 11.567-5.286-5.011-3.714 3.716 9 8.728 15-15.285z" />
                    </svg>
                    <span className="flex-grow text-[12px] capitalize font-bold" style={{ textAlign: "left" }}>{theme}</span>
                    <div className="flex h-full shrink-0 flex-wrap gap-1">
                      <div className="bg-primary w-1.5 h-3 rounded-full"></div>
                      <div className="bg-secondary w-1.5 h-3 rounded-full"></div>
                      <div className="bg-accent w-1.5 h-3 rounded-full"></div>
                      <div className="bg-neutral w-1.5 h-3 rounded-full"></div>
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="divider m-0 px-3 opacity-30"></div>

        {/* Fonts Section */}
        <div className="p-3">
          <h4 className="text-[10px] font-black uppercase tracking-widest text-base-content/50 mb-2 px-1 text-left">Typography</h4>
          <div className="grid grid-cols-1 gap-1">
            {FONTS.map((font) => (
              <button
                key={font.id}
                onClick={() => setFont(font.id)}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors hover:bg-base-300 ${currentFont === font.id ? 'bg-base-300 font-bold' : 'text-base-content'}`}
                style={{ fontFamily: `var(--font-family, ${font.name})` }} // Just for previewing in the dropdown if possible, otherwise it falls back
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="12"
                  height="12"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  className={`shrink-0 ${currentFont === font.id ? '' : 'invisible'}`}
                >
                  <path d="M20.285 2l-11.285 11.567-5.286-5.011-3.714 3.716 9 8.728 15-15.285z" />
                </svg>
                <span className="text-[12px]">{font.name}</span>
              </button>
            ))}
          </div>
        </div>
        
      </div>
    </div>
  );
}
