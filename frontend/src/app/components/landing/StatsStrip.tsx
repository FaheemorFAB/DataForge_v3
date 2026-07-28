import React, { useEffect } from "react";

export default function StatsStrip() {
  useEffect(() => {
    const items = document.querySelectorAll('.stat-strip-inner.reveal');
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
    <section style={{ borderTop: "1px solid var(--border)", background: "#1C1B18", padding: 0 }}>
      <div className="max-w-6xl mx-auto px-5 md:px-8">
        <div className="stat-strip-inner reveal">
          <div className="stat-glow">
            <div className="n">4.2<span className="accent-n">M</span></div>
            <p className="text-[10px] font-bold uppercase tracking-widest mt-3" style={{ color: "#8A8778", letterSpacing: ".12em" }}>Rows processed</p>
          </div>
          <div className="stat-glow">
            <div className="n">96<span className="accent-n">%</span></div>
            <p className="text-[10px] font-bold uppercase tracking-widest mt-3" style={{ color: "#8A8778", letterSpacing: ".12em" }}>Avg. data quality score</p>
          </div>
          <div className="stat-glow">
            <div className="n">&lt;3<span className="accent-n">s</span></div>
            <p className="text-[10px] font-bold uppercase tracking-widest mt-3" style={{ color: "#8A8778", letterSpacing: ".12em" }}>Time to first insight</p>
          </div>
          <div className="stat-glow">
            <div className="n" style={{ color: "#fff" }}>0</div>
            <p className="text-[10px] font-bold uppercase tracking-widest mt-3" style={{ color: "#8A8778", letterSpacing: ".12em" }}>Lines of code required</p>
          </div>
        </div>
      </div>
    </section>
  );
}
