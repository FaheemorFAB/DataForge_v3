import React, { useEffect } from "react";

export default function BuiltFor() {
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
      <div className="max-w-6xl mx-auto px-5 md:px-8">
        <div className="reveal max-w-lg mb-10">
          <p className="section-eyebrow mb-3">Built for</p>
          <h2 className="text-3xl md:text-4xl font-black tracking-tight" style={{ color: "var(--txt)" }}>
            Whoever&apos;s holding the dataset.
          </h2>
          <p className="text-xs md:text-xm" style={{ color: "var(--txt-m)" }}>DataForge is aimed at people who need answers from data, not another tool to learn.</p>
        </div>
        <div className="reveal space-y-4">
          {/* Row 1 */}
          <div className="flex items-center justify-between py-4 border-b" style={{ borderColor: "var(--border)" }}>
            <div className="flex items-center gap-6 flex-1">
              <div className="feat-ic flex-shrink-0" style={{ marginBottom: 0, background: "rgba(46,91,255,0.08)", borderColor: "rgba(46,91,255,0.15)" }}>
                <svg className="w-4 h-4" style={{ color: "var(--accent)" }} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
                </svg>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-12 gap-2 flex-1 items-center">
                <span className="text-sm font-bold md:col-span-3" style={{ color: "var(--txt)" }}>Business analysts</span>
                <span className="text-xs md:col-span-9" style={{ color: "var(--txt-m)" }}>Sales, revenue, and KPI analysis without writing Python.</span>
              </div>
            </div>
            <span className="text-[10px] font-mono pl-4" style={{ color: "var(--txt-m)" }}>01</span>
          </div>
          {/* Row 2 */}
          <div className="flex items-center justify-between py-4 border-b" style={{ borderColor: "var(--border)" }}>
            <div className="flex items-center gap-6 flex-1">
              <div className="feat-ic flex-shrink-0" style={{ marginBottom: 0, background: "rgba(46,91,255,0.08)", borderColor: "rgba(46,91,255,0.15)" }}>
                <svg className="w-4 h-4" style={{ color: "var(--accent)" }} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
                </svg>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-12 gap-2 flex-1 items-center">
                <span className="text-sm font-bold md:col-span-3" style={{ color: "var(--txt)" }}>Academic researchers</span>
                <span className="text-xs md:col-span-9" style={{ color: "var(--txt-m)" }}>Exploratory analysis and model prototyping for thesis work.</span>
              </div>
            </div>
            <span className="text-[10px] font-mono pl-4" style={{ color: "var(--txt-m)" }}>02</span>
          </div>
          {/* Row 3 */}
          <div className="flex items-center justify-between py-4 border-b" style={{ borderColor: "var(--border)" }}>
            <div className="flex items-center gap-6 flex-1">
              <div className="feat-ic flex-shrink-0" style={{ marginBottom: 0, background: "rgba(46,91,255,0.08)", borderColor: "rgba(46,91,255,0.15)" }}>
                <svg className="w-4 h-4" style={{ color: "var(--accent)" }} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5" />
                </svg>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-12 gap-2 flex-1 items-center">
                <span className="text-sm font-bold md:col-span-3" style={{ color: "var(--txt)" }}>Product managers</span>
                <span className="text-xs md:col-span-9" style={{ color: "var(--txt-m)" }}>User behaviour and funnel analysis straight from exported CSVs.</span>
              </div>
            </div>
            <span className="text-[10px] font-mono pl-4" style={{ color: "var(--txt-m)" }}>03</span>
          </div>
          {/* Row 4 */}
          <div className="flex items-center justify-between py-4 border-b" style={{ borderColor: "var(--border)" }}>
            <div className="flex items-center gap-6 flex-1">
              <div className="feat-ic flex-shrink-0" style={{ marginBottom: 0, background: "rgba(46,91,255,0.08)", borderColor: "rgba(46,91,255,0.15)" }}>
                <svg className="w-4 h-4" style={{ color: "var(--accent)" }} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.26 10.147a60.436 60.436 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.57 50.57 0 00-2.658-.813A59.905 59.905 0 0112 3.493a59.902 59.902 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.697 50.697 0 0112 13.489a50.702 50.702 0 017.74-3.342" />
                </svg>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-12 gap-2 flex-1 items-center">
                <span className="text-sm font-bold md:col-span-3" style={{ color: "var(--txt)" }}>Students</span>
                <span className="text-xs md:col-span-9" style={{ color: "var(--txt-m)" }}>Learning data science concepts through a working, automated pipeline.</span>
              </div>
            </div>
            <span className="text-[10px] font-mono pl-4" style={{ color: "var(--txt-m)" }}>04</span>
          </div>
          {/* Row 5 */}
          <div className="flex items-center justify-between py-4" style={{ borderColor: "var(--border)" }}>
            <div className="flex items-center gap-6 flex-1">
              <div className="feat-ic flex-shrink-0" style={{ marginBottom: 0, background: "rgba(46,91,255,0.08)", borderColor: "rgba(46,91,255,0.15)" }}>
                <svg className="w-4 h-4" style={{ color: "var(--accent)" }} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21" />
                </svg>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-12 gap-2 flex-1 items-center">
                <span className="text-sm font-bold md:col-span-3" style={{ color: "var(--txt)" }}>SME decision makers</span>
                <span className="text-xs md:col-span-9" style={{ color: "var(--txt-m)" }}>Reporting on business metrics without hiring a data team.</span>
              </div>
            </div>
            <span className="text-[10px] font-mono pl-4" style={{ color: "var(--txt-m)" }}>05</span>
          </div>
        </div>
      </div>
    </section>
  );
}
