import React, { useEffect } from "react";

export default function FeatureGrid() {
  useEffect(() => {
    // Scroll reveal observer for this component
    const items = document.querySelectorAll('.feat-card');
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
        <div className="reveal in max-w-lg mb-14">
          <p className="section-eyebrow mb-3">The workspace</p>
          <h2 className="text-3xl md:text-4xl font-black tracking-tight" style={{ color: "var(--txt)" }}>Six tools.<br />One pipeline.</h2>
          <p className="text-xs mt-4" style={{ color: "var(--txt-m)" }}>Every stage of the analysis lives behind one upload — no switching between notebooks, spreadsheets, and BI tools.</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="gc feat-card reveal" style={{ position: "relative", overflow: "hidden" }}>
            <div className="feat-ic"><svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9.53 16.122a3 3 0 00-5.78 1.128 2.25 2.25 0 01-2.4 2.245 4.5 4.5 0 008.4-2.245c0-.399-.078-.78-.22-1.128zm0 0a15.998 15.998 0 003.388-1.62m-5.043-.025a15.994 15.994 0 011.622-3.395m3.42 3.42a15.995 15.995 0 004.764-4.648l3.876-5.814a1.151 1.151 0 00-1.597-1.597L14.146 6.32a15.996 15.996 0 00-4.649 4.763m3.42 3.42a6.776 6.776 0 00-3.42-3.42" /></svg></div>
            <h3 className="text-sm font-bold mb-1.5" style={{ color: "var(--txt)" }}>Cleaning</h3>
            <p className="text-xs leading-relaxed" style={{ color: "var(--txt-m)" }}>Missing values, whitespace, and column naming fixed automatically, with a before/after diff.</p>
            <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: "60px", background: "linear-gradient(to top, rgba(255,79,51,0.07), transparent)", pointerEvents: "none" }}></div>
          </div>
          <div className="gc feat-card reveal" style={{ position: "relative", overflow: "hidden" }}>
            <div className="feat-ic"><svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" /></svg></div>
            <h3 className="text-sm font-bold mb-1.5" style={{ color: "var(--txt)" }}>Dashboard</h3>
            <p className="text-xs leading-relaxed" style={{ color: "var(--txt-m)" }}>Build bar, line, scatter, pie, and box plots on any column and pin them for later.</p>
            <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: "60px", background: "linear-gradient(to top, rgba(46,91,255,0.07), transparent)", pointerEvents: "none" }}></div>
          </div>
          <div className="gc feat-card reveal" style={{ position: "relative", overflow: "hidden" }}>
            <div className="feat-ic"><svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" /></svg></div>
            <h3 className="text-sm font-bold mb-1.5" style={{ color: "var(--txt)" }}>EDA</h3>
            <p className="text-xs leading-relaxed" style={{ color: "var(--txt-m)" }}>Automated Exploratory Data Analysis reports to instantly uncover distributions, correlations, and anomalies.</p>
            <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: "60px", background: "linear-gradient(to top, rgba(46,91,255,0.07), transparent)", pointerEvents: "none" }}></div>
          </div>
          <div className="gc feat-card reveal" style={{ position: "relative", overflow: "hidden" }}>
            <div className="feat-ic"><svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 10-7.517 0c.85.493 1.509 1.333 1.509 2.316V18" /></svg></div>
            <h3 className="text-sm font-bold mb-1.5" style={{ color: "var(--txt)" }}>Insights</h3>
            <p className="text-xs leading-relaxed" style={{ color: "var(--txt-m)" }}>Anomalies, key drivers, and risks surfaced automatically — no query required.</p>
            <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: "60px", background: "linear-gradient(to top, rgba(30,153,2,0.07), transparent)", pointerEvents: "none" }}></div>
          </div>
          <div className="gc feat-card reveal" style={{ position: "relative", overflow: "hidden" }}>
            <div className="feat-ic"><svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" /></svg></div>
            <h3 className="text-sm font-bold mb-1.5" style={{ color: "var(--txt)" }}>AI Query</h3>
            <p className="text-xs leading-relaxed" style={{ color: "var(--txt-m)" }}>Ask your dataset a question in plain English and get an answer grounded in the actual rows, via Gemini.</p>
            <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: "60px", background: "linear-gradient(to top, rgba(46,91,255,0.07), transparent)", pointerEvents: "none" }}></div>
          </div>
          <div className="gc feat-card reveal" style={{ position: "relative", overflow: "hidden" }}>
            <div className="feat-ic"><svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z" /></svg></div>
            <h3 className="text-sm font-bold mb-1.5" style={{ color: "var(--txt)" }}>AutoML</h3>
            <p className="text-xs leading-relaxed" style={{ color: "var(--txt-m)" }}>FLAML picks and tunes a model for your target column, then hands you a leaderboard and a downloadable .pkl.</p>
            <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: "60px", background: "linear-gradient(to top, rgba(255,79,51,0.07), transparent)", pointerEvents: "none" }}></div>
          </div>
        </div>
      </div>
    </section>
  );
}
