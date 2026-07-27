"use client";

import React, { useEffect } from "react";
import { Globe, Mail, MessageSquare, User } from "lucide-react";

const TEAM_MEMBERS = [
  {
    name: "Mohammad Numan",
    role: "Team-Lead | Full-Stack Dev",
    gradient: "linear-gradient(135deg, #2E5BFF 0%, #6B8BFF 100%)",
    linkedin: "https://www.linkedin.com/in/numan10",
    email: "mailto:9256fa@gmail.com",
    portfolio: "https://portfolio-seven-silk-82.vercel.app",
    github: "",
  },
  {
    name: "Mohammad Usman",
    role: "AI/ML Engineer",
    gradient: "linear-gradient(135deg, #1E9902 0%, #4CD137 100%)",
    linkedin: "https://www.linkedin.com/in/mohammad-usman-dar-264a6135b",
    portfolio: "",
    github: "https://github.com/MohammadUsman00",
  },
  {
    name: "Mubashir Shabir",
    role: "Front-End Dev",
    gradient: "linear-gradient(135deg, #8A2BE2 0%, #B82BE2 100%)",
    linkedin: "https://www.linkedin.com/in/mubashir-shabir-9704652bb/",
    portfolio: "",
    github: "https://github.com/Mubashir-546",
  },
  {
    name: "Faheem Ahmad Bhat",
    role: "Full-Stack Engineer | UI/UX",
    gradient: "linear-gradient(135deg, #FF4F33 0%, #FF8E53 100%)",
    linkedin: "#",
    portfolio: "#",
    github: "",
  },
];

export default function TeamSection() {
  useEffect(() => {
    // Scroll reveal observer for this component
    const items = document.querySelectorAll(".team-reveal");
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("in");
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15 }
    );
    items.forEach((el) => io.observe(el));

    return () => io.disconnect();
  }, []);

  return (
    <section className="section overflow-hidden">
      <div className="max-w-6xl mx-auto px-5 md:px-8">
        <div className="team-reveal reveal max-w-2xl mx-auto text-center mb-16">
          <p className="section-eyebrow mb-3">The DataForge Team</p>
          <h2
            className="text-3xl md:text-5xl font-black tracking-tight"
            style={{ color: "var(--txt)" }}
          >
            Meet the Builders.
          </h2>
          <p className="text-sm mt-4 md:text-base max-w-xl mx-auto" style={{ color: "var(--txt-m)" }}>
            We are a team of 4 passionate engineers and designers on a mission to turn data chaos into clarity.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {TEAM_MEMBERS.map((member, idx) => (
            <div
              key={idx}
              className="gc feat-card team-reveal reveal group relative overflow-hidden flex flex-col items-center text-center transition-all duration-500"
              style={{
                transitionDelay: `${idx * 100}ms`,
                padding: "2.5rem 1.5rem",
              }}
            >
              {/* Background Glow */}
              <div
                className="absolute -top-24 -right-24 w-48 h-48 rounded-full blur-[80px] opacity-0 group-hover:opacity-30 transition-opacity duration-700 pointer-events-none"
                style={{ background: member.gradient }}
              ></div>

              {/* Avatar */}
              <div className="relative mb-6">
                <div
                  className="w-24 h-24 rounded-full flex items-center justify-center relative z-10"
                  style={{
                    background: "rgba(255,255,255,0.03)",
                    border: "1px solid rgba(255,255,255,0.1)",
                  }}
                >
                  <User className="w-10 h-10" style={{ color: "var(--txt-m)" }} />
                </div>
                {/* Avatar Glow Ring */}
                <div
                  className="absolute inset-0 rounded-full scale-[1.15] opacity-0 group-hover:opacity-100 group-hover:scale-100 transition-all duration-500"
                  style={{
                    background: member.gradient,
                    maskImage:
                      "radial-gradient(transparent 65%, black 66%)",
                    WebkitMaskImage:
                      "radial-gradient(transparent 65%, black 66%)",
                  }}
                ></div>
              </div>

              {/* Info */}
              <h3 className="text-lg font-bold mb-1" style={{ color: "var(--txt)" }}>
                {member.name}
              </h3>
              <p
                className="text-xs font-semibold tracking-wide uppercase mb-6"
                style={{
                  background: member.gradient,
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                }}
              >
                {member.role}
              </p>

              {/* Social Links */}
              <div className="flex items-center gap-3 mt-auto relative z-10">
                {member.linkedin && (
                  <a
                    href={member.linkedin}
                    target="_blank"
                    rel="noreferrer"
                    className="w-9 h-9 rounded-full flex items-center justify-center transition-all duration-300 transform group-hover:-translate-y-1"
                    style={{
                      background: "rgba(255,255,255,0.03)",
                      border: "1px solid rgba(255,255,255,0.08)",
                      color: "var(--txt-m)",
                    }}
                    onMouseOver={(e) => {
                      e.currentTarget.style.color = "var(--txt)";
                      e.currentTarget.style.borderColor = "var(--txt)";
                    }}
                    onMouseOut={(e) => {
                      e.currentTarget.style.color = "var(--txt-m)";
                      e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)";
                    }}
                  >
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z" />
                    </svg>
                  </a>
                )}

                {member.portfolio && (
                  <a
                    href={member.portfolio}
                    target="_blank"
                    rel="noreferrer"
                    className="w-9 h-9 rounded-full flex items-center justify-center transition-all duration-300 transform group-hover:-translate-y-1 delay-150"
                    style={{
                      background: "rgba(255,255,255,0.03)",
                      border: "1px solid rgba(255,255,255,0.08)",
                      color: "var(--txt-m)",
                    }}
                    onMouseOver={(e) => {
                      e.currentTarget.style.color = "var(--txt)";
                      e.currentTarget.style.borderColor = "var(--txt)";
                    }}
                    onMouseOut={(e) => {
                      e.currentTarget.style.color = "var(--txt-m)";
                      e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)";
                    }}
                  >
                    <Globe className="w-4 h-4" />
                  </a>
                )}
                {member.github && (
                  <a
                    href={member.github}
                    target="_blank"
                    rel="noreferrer"
                    className="w-9 h-9 rounded-full flex items-center justify-center transition-all duration-300 transform group-hover:-translate-y-1 delay-150"
                    style={{
                      background: "rgba(255,255,255,0.03)",
                      border: "1px solid rgba(255,255,255,0.08)",
                      color: "var(--txt-m)",
                    }}
                    onMouseOver={(e) => {
                      e.currentTarget.style.color = "var(--txt)";
                      e.currentTarget.style.borderColor = "var(--txt)";
                    }}
                    onMouseOut={(e) => {
                      e.currentTarget.style.color = "var(--txt-m)";
                      e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)";
                    }}
                  >
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                    </svg>
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section >
  );
}
