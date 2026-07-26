import React, { useEffect } from "react";

export default function FAQ() {
  useEffect(() => {
    const items = document.querySelectorAll('.reveal');
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('in');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15 });
    items.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  return (
    <section className="section">
      <div className="max-w-3xl mx-auto px-5 md:px-8">
        <p className="section-eyebrow mb-3 reveal">Questions</p>
        <h2 className="text-3xl md:text-4xl font-black tracking-tight mb-10 reveal" style={{ color: "var(--txt)" }}>Before you upload.</h2>
        <div className="space-y-3 reveal">
          <details className="gc faq-item rounded-xl px-5 py-4">
            <summary className="flex items-center justify-between cursor-pointer list-none">
              <span className="text-sm font-bold" style={{ color: "var(--txt)" }}>Where does my data go?</span>
              <svg className="w-4 h-4 flex-shrink-0" style={{ color: "var(--txt-m)" }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
              </svg>
            </summary>
            <p className="text-xs mt-3 leading-relaxed" style={{ color: "var(--txt-m)" }}>
              Your file is processed for the session and never shared externally. Sign-in is required only so you can resume a project later.
            </p>
          </details>
          <details className="gc faq-item rounded-xl px-5 py-4">
            <summary className="flex items-center justify-between cursor-pointer list-none">
              <span className="text-sm font-bold" style={{ color: "var(--txt)" }}>What file formats are supported?</span>
              <svg className="w-4 h-4 flex-shrink-0" style={{ color: "var(--txt-m)" }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
              </svg>
            </summary>
            <p className="text-xs mt-3 leading-relaxed" style={{ color: "var(--txt-m)" }}>
              CSV up to 200MB, or a Google Sheet shared as &quot;Anyone with the link can view.&quot;
            </p>
          </details>
          <details className="gc faq-item rounded-xl px-5 py-4">
            <summary className="flex items-center justify-between cursor-pointer list-none">
              <span className="text-sm font-bold" style={{ color: "var(--txt)" }}>Do I need to know Python or SQL?</span>
              <svg className="w-4 h-4 flex-shrink-0" style={{ color: "var(--txt-m)" }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
              </svg>
            </summary>
            <p className="text-xs mt-3 leading-relaxed" style={{ color: "var(--txt-m)" }}>
              No. Cleaning, EDA, and modelling run automatically. The AI Query tab lets you ask follow-up questions in plain English.
            </p>
          </details>
        </div>
      </div>
    </section>
  );
}
