"use client";

import React, { useState, useEffect, useRef } from "react";
import { useWorkspace } from "./WorkspaceProvider";
import { apiFetch } from "@/lib/api";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  RadialLinearScale,
  Title,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";
import { Scatter, Line, Bar, Pie, Doughnut } from "react-chartjs-2";
import { Check, X, Loader2, Copy, AlertTriangle, Sparkles, Download, Info, Cpu, GitFork, BarChart3, Wrench } from "lucide-react";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  RadialLinearScale,
  Title,
  Tooltip,
  Legend,
  Filler
);

function ChatMessageChart({ chartData }: { chartData: any }) {
  const chartRef = useRef<any>(null);
  const initialType = (chartData.type || "bar_chart").toLowerCase();
  const [currentType, setCurrentType] = useState<string>(initialType);

  const downloadChartImage = () => {
    if (!chartRef.current) return;
    try {
      const url = chartRef.current.toBase64Image();
      const a = document.createElement("a");
      a.href = url;
      a.download = `${(chartData.title || "chart").toLowerCase().replace(/\\s+/g, "_")}.png`;
      a.click();
    } catch (e) {
      console.error("Failed to export chart image:", e);
    }
  };

  const labels = chartData.labels || [];
  const values = chartData.values || [];
  const palette = chartData.colors || [
    "#6366f1", "#8b5cf6", "#ec4899", "#06b6d4", "#10b981", "#f59e0b", "#f43f5e", "#3b82f6"
  ];

  const isLight = typeof document !== "undefined" && !["dark", "dracula", "slate", "emerald", "nord", "luxury", "night", "synthwave", "black"].includes(
    document.documentElement.getAttribute("data-theme") || "dark"
  );

  const textColor = isLight ? "#1e293b" : "#d4d4d8";
  const gridColor = isLight ? "rgba(0,0,0,0.07)" : "rgba(255,255,255,0.08)";

  const isPieLike = ["pie_chart", "pie", "doughnut_chart", "doughnut"].includes(currentType);

  const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: isPieLike,
        position: "bottom" as const,
        labels: {
          color: textColor,
          boxWidth: 10,
          font: { size: 10 },
          padding: 8,
        },
      },
      tooltip: {
        backgroundColor: "rgba(15, 23, 42, 0.95)",
        titleColor: "#ffffff",
        bodyColor: "#cbd5e1",
        borderColor: "rgba(99, 102, 241, 0.4)",
        borderWidth: 1,
        padding: 8,
        displayColors: true,
      },
    },
    scales: isPieLike ? undefined : {
      x: {
        grid: { color: gridColor },
        ticks: { color: textColor, font: { size: 10 }, maxRotation: 45 },
      },
      y: {
        grid: { color: gridColor },
        ticks: { color: textColor, font: { size: 10 } },
      },
    },
  };

  const chartDataObj = {
    labels: labels.slice(0, 10),
    datasets: [
      {
        label: chartData.y_label || "Value",
        data: values.slice(0, 10),
        backgroundColor: isPieLike
          ? palette.slice(0, labels.length)
          : palette[0],
        borderColor: isPieLike
          ? (isLight ? "#e2e8f0" : "#09090b")
          : palette[0],
        borderWidth: 1,
        borderRadius: currentType === "bar_chart" ? 4 : 0,
        tension: currentType === "line_chart" ? 0.35 : 0,
        fill: currentType === "line_chart" ? { target: "origin", above: isLight ? "rgba(99, 102, 241, 0.12)" : "rgba(99, 102, 241, 0.15)" } : false,
      },
    ],
  };

  const scatterDataObj = chartData.points ? {
    datasets: [
      {
        label: `${chartData.x_label} vs ${chartData.y_label}`,
        data: chartData.points,
        backgroundColor: "#6366f1",
        borderColor: "#818cf8",
        borderWidth: 1,
        pointRadius: 4,
        pointHoverRadius: 6,
      },
    ],
  } : null;

  return (
    <div
      className="p-3 rounded-xl border shadow-md my-2.5 space-y-2"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border)",
      }}
    >
      <div
        className="flex items-center justify-between text-[11px] pb-1.5 border-b"
        style={{ borderColor: "var(--border)" }}
      >
        <span
          className="font-semibold truncate max-w-[200px]"
          style={{ color: "var(--txt)" }}
        >
          {chartData.title || `${chartData.x_label || "Dimension"} Analysis`}
        </span>
        <button
          type="button"
          onClick={downloadChartImage}
          title="Download Chart as PNG"
          className="p-1 rounded transition-colors cursor-pointer flex items-center gap-1 text-[10px]"
          style={{ color: "var(--txt-m)" }}
        >
          <Download size={12} />
          <span>PNG</span>
        </button>
      </div>

      <div className="relative w-full h-56 pt-1">
        {currentType === "scatter_chart" && scatterDataObj ? (
          <Scatter ref={chartRef} data={scatterDataObj} options={commonOptions as any} />
        ) : isPieLike ? (
          currentType === "doughnut_chart" || currentType === "doughnut" ? (
            <Doughnut ref={chartRef} data={chartDataObj} options={commonOptions as any} />
          ) : (
            <Pie ref={chartRef} data={chartDataObj} options={commonOptions as any} />
          )
        ) : currentType === "line_chart" ? (
          <Line ref={chartRef} data={chartDataObj} options={commonOptions as any} />
        ) : (
          <Bar ref={chartRef} data={chartDataObj} options={commonOptions as any} />
        )}
      </div>

      {/* Quick Chart Type Switcher */}
      {labels.length > 0 && currentType !== "scatter_chart" && (
        <div
          className="flex items-center justify-end gap-1 pt-1.5 border-t text-[10px]"
          style={{ borderColor: "var(--border)" }}
        >
          {[
            { id: "bar_chart", label: "Bar" },
            { id: "pie_chart", label: "Pie" },
            { id: "doughnut_chart", label: "Donut" },
            { id: "line_chart", label: "Line" },
          ].map((typeItem) => (
            <button
              key={typeItem.id}
              type="button"
              onClick={() => setCurrentType(typeItem.id)}
              className="px-2 py-0.5 rounded transition-all cursor-pointer font-medium"
              style={{
                background: currentType === typeItem.id ? "var(--accent)" : "transparent",
                color: currentType === typeItem.id ? "#ffffff" : "var(--txt-m)",
                fontWeight: currentType === typeItem.id ? 700 : 500,
              }}
            >
              {typeItem.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function CodeBlock({ code, lang }: { code: string; lang: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-2.5 rounded-xl overflow-hidden border border-zinc-700/60 bg-black/60 shadow-md">
      <div className="flex items-center justify-between px-3 py-1.5 bg-zinc-900/90 border-b border-zinc-800 text-[10px]">
        <span className="font-mono font-bold tracking-wider uppercase text-indigo-300">
          {lang || "python"}
        </span>
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1 text-zinc-400 hover:text-white transition-colors cursor-pointer"
        >
          {copied ? <Check size={11} className="text-emerald-400" /> : <Copy size={11} />}
          <span>{copied ? "Copied" : "Copy"}</span>
        </button>
      </div>
      <pre className="p-3 font-mono text-[11px] text-zinc-200 overflow-x-auto leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function renderInlineMarkdown(text: string) {
  // Replace pattern *'...' * or *"..." * with clean quotes "..."
  const cleanLine = text.replace(/\*['"](.*?)['"]\*/g, '"$1"');
  const parts = cleanLine.split(/(\*\*.*?\*\*|`.*?`|\*.*?\*)/g);

  return parts.map((part, pIdx) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length >= 4) {
      return (
        <strong key={pIdx} className="font-bold" style={{ color: "var(--txt)" }}>
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("`") && part.endsWith("`") && part.length >= 2) {
      return (
        <code
          key={pIdx}
          className="px-1.5 py-0.5 rounded font-mono text-[11px] font-semibold border"
          style={{
            background: "var(--inp-bg)",
            borderColor: "var(--border)",
            color: "var(--accent-ink, var(--accent))",
          }}
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    if (part.startsWith("*") && part.endsWith("*") && part.length >= 2) {
      return (
        <span key={pIdx} className="italic" style={{ color: "var(--txt-m)" }}>
          {part.slice(1, -1)}
        </span>
      );
    }
    return part;
  });
}

function renderTextParagraphs(rawText: string, keyPrefix: string) {
  const lines = rawText.split("\n");
  return (
    <div key={keyPrefix} className="space-y-1">
      {lines.map((line, lIdx) => {
        const trimmed = line.trim();
        if (!trimmed) {
          return <div key={lIdx} className="h-1" />;
        }
        // Heading 3
        if (trimmed.startsWith("### ")) {
          return (
            <h4
              key={lIdx}
              className="text-xs font-black tracking-wider uppercase pt-2 pb-0.5 border-b"
              style={{ color: "var(--accent)", borderColor: "var(--border)" }}
            >
              {trimmed.slice(4)}
            </h4>
          );
        }
        // Heading 2
        if (trimmed.startsWith("## ")) {
          return (
            <h3
              key={lIdx}
              className="text-sm font-black tracking-tight pt-2 pb-0.5"
              style={{ color: "var(--txt)" }}
            >
              {trimmed.slice(3)}
            </h3>
          );
        }
        // Bullet point
        if (trimmed.startsWith("• ") || trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
          const bulletContent = trimmed.slice(2);
          return (
            <div
              key={lIdx}
              className="flex items-start gap-2 py-0.5 text-xs leading-relaxed"
              style={{ color: "var(--txt)" }}
            >
              <span className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0" style={{ background: "var(--accent)" }} />
              <div className="flex-1" style={{ color: "var(--txt)" }}>{renderInlineMarkdown(bulletContent)}</div>
            </div>
          );
        }
        // Regular line
        return (
          <p key={lIdx} className="text-xs leading-relaxed" style={{ color: "var(--txt)" }}>
            {renderInlineMarkdown(line)}
          </p>
        );
      })}
    </div>
  );
}

function FormattedMessage({ text }: { text: string }) {
  if (!text) return null;

  // Split content by code blocks ```...```
  const codeBlockRegex = /```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g;
  const segments: React.ReactNode[] = [];
  let lastIndex = 0;
  let match;

  while ((match = codeBlockRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      const rawText = text.substring(lastIndex, match.index);
      segments.push(renderTextParagraphs(rawText, `text-${lastIndex}`));
    }
    const lang = match[1] || "python";
    const code = match[2];
    segments.push(<CodeBlock key={`code-${match.index}`} code={code} lang={lang} />);
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    segments.push(renderTextParagraphs(text.substring(lastIndex), `text-${lastIndex}`));
  }

  return <div className="space-y-1.5 text-sm leading-relaxed">{segments}</div>;
}

export function ChatSidebar() {
  const { uploadId } = useWorkspace();
  const [chatSessions, setChatSessions] = useState<any[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [query, setQuery] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [chatSidebarOpen, setChatSidebarOpen] = useState(true);
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [editingSessionName, setEditingSessionName] = useState("");
  const [deleteConfirmSessionId, setDeleteConfirmSessionId] = useState<string | null>(null);
  const [deletingSessionId, setDeletingSessionId] = useState<string | null>(null);
  const [aiPermissionGranted, setAiPermissionGranted] = useState(false);

  const threadRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const quickActions = [
    "Summarize the key trends",
    "Show a correlation matrix",
    "What are the top 5 anomalies?",
    "Show summary of dataset",
    "Identify data quality issues",
  ];

  // Fetch initial sessions & consent on uploadId change
  useEffect(() => {
    if (uploadId) {
      loadSessions();
    }
  }, [uploadId]);

  const loadSessions = async () => {
    if (!uploadId) return;
    try {
      const res = await apiFetch(`/workspace/state?upload_id=${encodeURIComponent(uploadId)}`);
      if (res.ok) {
        const st = await res.json();
        if (st.ai_consent) {
          setAiPermissionGranted(true);
        }
        const sessions = Array.isArray(st.chat_sessions) ? st.chat_sessions : [];
        if (sessions.length > 0) {
          setChatSessions(sessions);
        }
        const activeId = st.active_session_id || (sessions.length > 0 ? sessions[0].id : null);
        if (activeId) {
          setActiveSessionId(activeId);
        }
        if (st.chat_history && Array.isArray(st.chat_history) && st.chat_history.length > 0) {
          setMessages(st.chat_history);
        } else if (sessions.length > 0) {
          const matched = sessions.find((s: any) => s.id === activeId) || sessions[0];
          if (matched && Array.isArray(matched.messages)) {
            setMessages(matched.messages);
          }
        }
      }
    } catch (e) {
      console.error("Failed to load chat sessions:", e);
    }
  };

  const handleAcceptConsent = async () => {
    setAiPermissionGranted(true);
    if (!uploadId) return;
    try {
      await apiFetch(`/workspace/consent?upload_id=${encodeURIComponent(uploadId)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ upload_id: uploadId, consent: true }),
      });
      loadSessions();
    } catch (e) {
      console.error("Failed to save AI consent:", e);
    }
  };

  const createChatSession = async () => {
    if (!uploadId) return;
    try {
      const res = await apiFetch(`/workspace/chat/session?upload_id=${encodeURIComponent(uploadId)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ upload_id: uploadId, name: "New Chat" }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.chat_sessions) setChatSessions(data.chat_sessions);
        const newId = data.active_session || data.active_session_id || (data.session && data.session.id);
        if (newId) setActiveSessionId(newId);
        setMessages([]);
        if (window.innerWidth < 768) setChatSidebarOpen(false);
      }
    } catch (e) {
      console.error("Failed to create chat session:", e);
    }
  };

  const selectChatSession = async (id: string) => {
    if (window.innerWidth < 768) setChatSidebarOpen(false);
    if (id === activeSessionId) return;

    // Instant optimistic switch from local in-memory session cache
    const targetSess = chatSessions.find((s) => s.id === id);
    if (targetSess && Array.isArray(targetSess.messages)) {
      setMessages(targetSess.messages);
    }
    setActiveSessionId(id);

    if (!uploadId) return;
    try {
      const res = await apiFetch(
        `/workspace/chat/session/select?upload_id=${encodeURIComponent(uploadId)}&id=${encodeURIComponent(id)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ upload_id: uploadId, session_id: id }),
        }
      );
      if (res.ok) {
        const data = await res.json();
        if (data.chat_sessions) setChatSessions(data.chat_sessions);
        if (data.chat_history) setMessages(data.chat_history);
        scrollToBottom();
      }
    } catch (e) {
      console.error("Failed to select chat session:", e);
    }
  };

  const deleteChatSession = async (id: string) => {
    if (!uploadId) return;
    setDeletingSessionId(id);
    try {
      const res = await apiFetch(
        `/workspace/chat/session/${encodeURIComponent(id)}?upload_id=${encodeURIComponent(uploadId)}`,
        { method: "DELETE" }
      );
      if (res.ok) {
        const data = await res.json();
        if (data.chat_sessions) setChatSessions(data.chat_sessions);
        setMessages(data.chat_history || []);
        if (data.active_session) setActiveSessionId(data.active_session);
        else if (data.active_session_id) setActiveSessionId(data.active_session_id);
      }
    } catch (e) {
      console.error("Failed to delete chat session:", e);
    } finally {
      setDeletingSessionId(null);
      setDeleteConfirmSessionId(null);
    }
  };

  const startRenameSession = (id: string, currentName: string) => {
    setEditingSessionId(id);
    setEditingSessionName(currentName || "");
  };

  const renameChatSession = async (id: string) => {
    setEditingSessionId(null);
    if (!uploadId || !editingSessionName.trim()) return;
    try {
      const res = await apiFetch(
        `/workspace/chat/session/rename?upload_id=${encodeURIComponent(uploadId)}&id=${encodeURIComponent(id)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ upload_id: uploadId, session_id: id, name: editingSessionName.trim() }),
        }
      );
      if (res.ok) {
        const data = await res.json();
        if (data.chat_sessions) setChatSessions(data.chat_sessions);
      }
    } catch (e) {
      console.error("Failed to rename chat session:", e);
    }
  };

  const runQuery = async (q: string = query) => {
    if (!q.trim() || isAnalyzing || !uploadId) return;

    const targetSessionId = activeSessionId || "default";
    const newMessage = { role: "user", content: q.trim(), ts: Date.now() };

    setMessages((prev) => [...prev, newMessage]);
    setQuery("");
    setIsAnalyzing(true);
    scrollToBottom();

    try {
      const res = await apiFetch("/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: q.trim(),
          session_id: targetSessionId,
          upload_id: uploadId,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.chat_sessions) {
          setChatSessions(data.chat_sessions);
        }
        if (data.active_session_id) {
          setActiveSessionId(data.active_session_id);
        }
        if (data.reply) {
          setMessages((prev) => {
            const nextMsgs = [...prev, data.reply];
            setChatSessions((prevSessions) =>
              prevSessions.map((s) =>
                s.id === targetSessionId ? { ...s, messages: nextMsgs } : s
              )
            );
            return nextMsgs;
          });
        }
      } else {
        const errData = await res.json().catch(() => ({}));
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: errData.detail || errData.error || "Failed to analyze query. Please try again.",
          },
        ]);
      }
    } catch (e: any) {
      setMessages((prev) => [...prev, { role: "assistant", content: "Error: " + e.message }]);
    } finally {
      setIsAnalyzing(false);
      scrollToBottom();
    }
  };

  const scrollToBottom = () => {
    setTimeout(() => {
      if (threadRef.current) {
        threadRef.current.scrollTop = threadRef.current.scrollHeight;
      }
    }, 100);
  };

  const handleTextareaInput = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + "px";
    }
  };

  if (!aiPermissionGranted) {
    return (
      <div
        className="tab-panel space-y-5 px-4 py-4 md:px-6 md:py-6"
        style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}
      >
        <div
          className="gc rounded-2xl p-6 text-center max-w-md space-y-4 shadow-2xl border"
          style={{ background: "var(--surface)", borderColor: "var(--border)" }}
        >
          <div
            className="w-12 h-12 rounded-full flex items-center justify-center mx-auto"
            style={{ background: "rgba(46,91,255,.08)", color: "var(--accent)" }}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.57-.598-3.75h-.152c-3.196 0-6.1-1.249-8.25-3.286zm0 3v1.5m0 3v.008H12v-.008z"
              />
            </svg>
          </div>
          <h3 className="text-lg font-black uppercase tracking-tight" style={{ color: "var(--txt)" }}>
            AI Data Sharing Consent
          </h3>
          <p className="text-xs leading-relaxed" style={{ color: "var(--txt-m)" }}>
            To support AI Chat, DataForge sends segments of your current dataset profile, columns, and query text to
            Gemini models or processes them locally via the built-in deterministic analytics engine.
          </p>
          <div
            className="p-3 rounded-lg text-[11px] leading-relaxed text-left border space-y-1.5"
            style={{ background: "var(--bg)", borderColor: "var(--border)", color: "var(--txt-m)" }}
          >
            <div className="flex items-start gap-2">
              <Check size={14} className="text-emerald-500 flex-shrink-0" />
              <span>Only column metadata, statistics, and queries are shared.</span>
            </div>
            <div className="flex items-start gap-2">
              <Check size={14} className="text-emerald-500 flex-shrink-0" />
              <span>Full raw row contents are kept locally in your environment.</span>
            </div>
            <div className="flex items-start gap-2">
              <Check size={14} className="text-emerald-500 flex-shrink-0" />
              <span>Data is processed securely and is not used to train external models.</span>
            </div>
          </div>
          <p className="text-[10px]" style={{ color: "var(--txt-f)" }}>
            By clicking &quot;Accept &amp; Continue&quot;, you consent to enabling AI Chat for this dataset.
          </p>
          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={handleAcceptConsent}
              className="bp flex-1 text-xs py-2 justify-center"
              style={{ cursor: "pointer" }}
            >
              Accept &amp; Continue
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="tab-panel h-full flex flex-col relative" style={{ padding: 0 }}>
      <div className="chat-container">
        {/* Mobile Sidebar Overlay */}
        <div
          className={`chat-sidebar-overlay ${chatSidebarOpen ? "open" : ""}`}
          onClick={() => setChatSidebarOpen(false)}
        ></div>

        {/* Sidebar */}
        <div className={`chat-sidebar ${chatSidebarOpen ? "open" : "collapsed-desktop"}`}>
          <button className="chat-sidebar-btn" onClick={createChatSession}>
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            New Chat
          </button>
          <p className="chat-sidebar-label">History</p>
          <div className="chat-sessions-list">
            {chatSessions.map((s) => (
              <div
                key={s.id}
                className={`chat-session-item ${activeSessionId === s.id ? "active" : ""}`}
                onClick={() => selectChatSession(s.id)}
              >
                {editingSessionId === s.id ? (
                  <input
                    type="text"
                    value={editingSessionName}
                    onChange={(e) => setEditingSessionName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") renameChatSession(s.id);
                      if (e.key === "Escape") setEditingSessionId(null);
                    }}
                    onBlur={() => renameChatSession(s.id)}
                    onClick={(e) => e.stopPropagation()}
                    className="chat-rename-input"
                    autoFocus
                  />
                ) : (
                  <div className="flex items-center w-full min-w-0 gap-1">
                    <svg className="w-3 h-3 flex-shrink-0 opacity-40" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.5 48.172 48.172 0 003.423-.38c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
                    </svg>
                    <span className="chat-session-title truncate">{s.name || "Untitled Chat"}</span>
                    {deleteConfirmSessionId === s.id ? (
                      <div className="flex items-center gap-1 shrink-0" onClick={(e) => e.stopPropagation()}>
                        <button
                          type="button"
                          disabled={deletingSessionId === s.id}
                          onClick={() => deleteChatSession(s.id)}
                          className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold bg-red-600 text-white hover:bg-red-700 shadow-sm transition-all cursor-pointer"
                          title="Confirm permanent deletion"
                        >
                          {deletingSessionId === s.id ? (
                            <Loader2 size={10} className="animate-spin" />
                          ) : (
                            <Check size={10} />
                          )}
                          <span>Confirm?</span>
                        </button>
                        <button
                          type="button"
                          disabled={deletingSessionId === s.id}
                          onClick={() => setDeleteConfirmSessionId(null)}
                          className="p-1 rounded text-zinc-400 hover:text-white transition-all cursor-pointer"
                          title="Cancel"
                        >
                          <X size={10} />
                        </button>
                      </div>
                    ) : (
                      <div className="chat-session-actions" onClick={(e) => e.stopPropagation()}>
                        <button className="chat-action-btn" title="Rename" onClick={() => startRenameSession(s.id, s.name)}>
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487z" />
                          </svg>
                        </button>
                        <button className="chat-action-btn delete" title="Delete" onClick={() => setDeleteConfirmSessionId(s.id)}>
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                          </svg>
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
            {!chatSessions.length && (
              <div className="text-center py-8 opacity-40">
                <svg className="w-8 h-8 mx-auto mb-2" fill="none" stroke="currentColor" strokeWidth="1.2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 9.75a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375m-13.5 3.01c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.5 48.172 48.172 0 003.423-.38c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
                </svg>
                <p className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>
                  No chats yet
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Main Chat Area */}
        <div className="chat-main">
          {/* Header */}
          <div className="chat-header">
            <div className="flex items-center gap-2.5 min-w-0">
              <button onClick={() => setChatSidebarOpen(!chatSidebarOpen)} className="ibt flex-shrink-0" title="Toggle sidebar">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <rect x="3" y="3" width="18" height="18" rx="2" />
                  <path d="M9 3v18" />
                </svg>
              </button>
              <div className="min-w-0">
                <h3 className="font-black text-sm uppercase tracking-tight truncate" style={{ color: "var(--txt)" }}>
                  {chatSessions.find((s) => s.id === activeSessionId)?.name || "AI Chat"}
                </h3>
              </div>
            </div>
            <div className="flex items-center gap-1.5 flex-shrink-0">
              <div className="w-1.5 h-1.5 rounded-full" style={{ background: "#22c55e", boxShadow: "0 0 5px #22c55e" }}></div>
              <span className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>
                Analyst AI
              </span>
            </div>
          </div>

          {/* Thread */}
          <div id="chat-thread" ref={threadRef}>
            {!messages.length && (
              <div className="flex flex-col items-center justify-center py-12 gap-4 text-center">
                <div
                  className="w-14 h-14 rounded-2xl flex items-center justify-center text-2xl font-black italic"
                  style={{
                    background: "linear-gradient(135deg,var(--accent),rgba(99,102,241,.8))",
                    color: "#fff",
                    boxShadow: "0 8px 24px rgba(46,91,255,.3)",
                  }}
                >
                  AI
                </div>
                <div>
                  <p className="font-black text-base uppercase tracking-tight" style={{ color: "var(--txt)" }}>
                    DataForge Analyst
                  </p>
                  <p className="text-xs mt-1 max-w-xs" style={{ color: "var(--txt-m)" }}>
                    Ask me anything about your dataset — trends, stats, correlations, or custom queries.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2 justify-center max-w-sm">
                  {quickActions.map((action) => (
                    <button
                      key={action}
                      onClick={() => runQuery(action)}
                      className="chat-quick-chip"
                      disabled={isAnalyzing}
                    >
                      {action}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg, i) => (
              <div key={i} className={`chat-msg-wrap ${msg.role}`}>
                {msg.role === "assistant" ? (
                  <div className="w-full">
                    <div className="chat-ai-header">
                      <div className="chat-ai-avatar">AI</div>
                      <span className="chat-ai-name">DataForge Analyst</span>
                    </div>
                    <div className="chat-bubble-ai space-y-3">
                      {/* Specialized Agent Collaboration Badges */}
                      {msg.agent_actions && msg.agent_actions.length > 0 && (
                        <div className="flex flex-wrap items-center gap-1.5 pb-1">
                          {msg.agent_actions.map((act: any, aIdx: number) => {
                            const isClean = act.agent === "CleanerAgent";
                            const isML = act.agent === "AutoMLAgent";
                            const isPipe = act.agent === "PipelineAgent";
                            const bg = isClean ? "rgba(16,185,129,0.12)" : (isML ? "rgba(139,92,246,0.12)" : (isPipe ? "rgba(245,158,11,0.12)" : "rgba(59,130,246,0.12)"));
                            const border = isClean ? "rgba(16,185,129,0.3)" : (isML ? "rgba(139,92,246,0.3)" : (isPipe ? "rgba(245,158,11,0.3)" : "rgba(59,130,246,0.3)"));
                            const color = isClean ? "#059669" : (isML ? "#7c3aed" : (isPipe ? "#d97706" : "#2563eb"));
                            const icon = isClean ? <Wrench size={10} /> : (isML ? <Cpu size={10} /> : (isPipe ? <GitFork size={10} /> : <BarChart3 size={10} />));
                            return (
                              <span
                                key={aIdx}
                                className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[10px] font-bold border shadow-xs"
                                style={{ background: bg, borderColor: border, color }}
                                title={act.message}
                              >
                                {icon}
                                <span>{act.agent}</span>
                              </span>
                            );
                          })}
                        </div>
                      )}

                      {msg.content && <FormattedMessage text={msg.content} />}

                      {/* System Notice / Prepayment Credit Banner */}
                      {(msg.system_notice || (msg.insight && msg.insight.includes("[Notice]"))) && (
                        <div
                          className="p-3 rounded-xl border flex items-start gap-2.5 text-xs shadow-xs my-2"
                          style={{
                            background: "rgba(245, 158, 11, 0.08)",
                            borderColor: "rgba(245, 158, 11, 0.25)",
                            color: "#fbbf24",
                          }}
                        >
                          <AlertTriangle size={15} className="text-amber-400 shrink-0 mt-0.5" />
                          <div className="space-y-0.5 leading-snug">
                            <span className="font-bold text-amber-300">Offline Engine Active</span>
                            <p className="text-[11px] opacity-90">
                              {msg.system_notice || msg.insight.replace("[Notice]", "").trim()}
                            </p>
                          </div>
                        </div>
                      )}

                      {/* Analytical Insight (Only when distinct and containing genuine data findings) */}
                      {msg.insight && 
                       !msg.insight.includes("[Notice]") && 
                       !msg.insight.toLowerCase().startsWith("pipeline") &&
                       !msg.insight.toLowerCase().startsWith("cleaned dataset") &&
                       !msg.insight.toLowerCase().startsWith("formulated") &&
                       !(msg.content && msg.content.toLowerCase().includes(msg.insight.toLowerCase())) && (
                        <div
                          className="chat-insight-box p-2.5 rounded-lg text-xs border flex items-start gap-2 shadow-xs"
                          style={{
                            background: "var(--surface)",
                            borderColor: "var(--border)",
                            color: "var(--txt)",
                          }}
                        >
                          <Info size={14} className="shrink-0 mt-0.5" style={{ color: "var(--accent)" }} />
                          <span className="leading-snug" style={{ color: "var(--txt)" }}>{msg.insight}</span>
                        </div>
                      )}

                      {/* Visual Chart Card (Chart.js Component with Type Switcher & PNG Export) */}
                      {msg.chartData && (msg.chartData.labels || msg.chartData.points) && (
                        <ChatMessageChart chartData={msg.chartData} />
                      )}

                      {/* Download Clean Data links if provided */}
                      {msg.download_links && (
                        <div className="flex items-center gap-2 pt-1 text-[11px]">
                          <span className="font-medium" style={{ color: "var(--txt-m)" }}>Download Clean Dataset:</span>
                          {msg.download_links.csv && (
                            <a
                              href={msg.download_links.csv}
                              download
                              className="px-2.5 py-1 rounded-md border font-semibold transition-all inline-flex items-center gap-1 shadow-xs"
                              style={{
                                background: "rgba(16, 185, 129, 0.1)",
                                borderColor: "rgba(16, 185, 129, 0.4)",
                                color: "#059669",
                              }}
                            >
                              <Download size={11} /> CSV
                            </a>
                          )}
                          {msg.download_links.parquet && (
                            <a
                              href={msg.download_links.parquet}
                              download
                              className="px-2.5 py-1 rounded-md border font-semibold transition-all inline-flex items-center gap-1 shadow-xs"
                              style={{
                                background: "rgba(99, 102, 241, 0.1)",
                                borderColor: "rgba(99, 102, 241, 0.4)",
                                color: "var(--accent)",
                              }}
                            >
                              <Download size={11} /> Parquet
                            </a>
                          )}
                        </div>
                      )}

                      {/* Interactive Suggested Actions / Cross-Questioning Option Chips */}
                      {msg.suggested_actions && msg.suggested_actions.length > 0 && (
                        <div className="flex flex-wrap gap-2 pt-2">
                          {msg.suggested_actions.map((act: any, aIdx: number) => (
                            <button
                              key={aIdx}
                              type="button"
                              onClick={() => runQuery(act.query || act.label)}
                              className="chat-action-pill"
                            >
                              <span>{act.label}</span>
                            </button>
                          ))}
                        </div>
                      )}

                      {msg.tableData && msg.tableData.rows && msg.tableData.rows.length > 0 && (
                        <div
                          className="overflow-x-auto rounded-lg border mt-2 max-h-60"
                          style={{ borderColor: "var(--border)", background: "var(--surface)" }}
                        >
                          <table className="w-full text-left text-[11px] border-collapse">
                            <thead>
                              <tr className="border-b" style={{ borderColor: "var(--border)", background: "var(--bg)" }}>
                                {msg.tableData.headers?.map((h: string, idx: number) => (
                                  <th
                                    key={idx}
                                    className="p-2 font-bold whitespace-nowrap"
                                    style={{ color: "var(--txt-m)" }}
                                  >
                                    {h}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {msg.tableData.rows.slice(0, 10).map((row: any, rIdx: number) => (
                                <tr
                                  key={rIdx}
                                  className="border-b last:border-0 hover:bg-black/5 dark:hover:bg-white/5"
                                  style={{ borderColor: "var(--border)" }}
                                >
                                  {msg.tableData.headers?.map((h: string, cIdx: number) => (
                                    <td key={cIdx} className="p-2 whitespace-nowrap" style={{ color: "var(--txt)" }}>
                                      {row[h] !== null && row[h] !== undefined ? String(row[h]) : "—"}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                          {msg.tableData.total > 10 && (
                            <div className="p-1.5 text-center text-[10px] opacity-60" style={{ background: "var(--bg)" }}>
                              Showing 10 of {msg.tableData.total} rows
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div>
                    <div className="chat-bubble-user">{msg.content}</div>
                  </div>
                )}
              </div>
            ))}

            {isAnalyzing && (
              <div className="chat-typing">
                <div className="chat-typing-avatar">AI</div>
                <div className="chat-typing-bubble">
                  <div className="chat-dot"></div>
                  <div className="chat-dot"></div>
                  <div className="chat-dot"></div>
                  <span className="text-[10px] font-semibold ml-1" style={{ color: "var(--txt-m)" }}>
                    Coordinating Multi-Agent Analysis…
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="chat-input-wrap" style={{ margin: "1rem" }}>
            <textarea
              ref={textareaRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  runQuery();
                }
              }}
              placeholder="Ask anything about your data…"
              className="chat-textarea"
              rows={1}
              onInput={handleTextareaInput}
            />
            <button
              onClick={() => runQuery()}
              disabled={isAnalyzing || !query.trim()}
              className="chat-send-btn"
            >
              {!isAnalyzing ? (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
                </svg>
              ) : (
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
              )}
            </button>
          </div>
          <p className="chat-input-hint text-center pb-2 text-[10px]" style={{ color: "var(--txt-m)" }}>
            Shift+Enter for new line · Enter to send
          </p>
        </div>
      </div>
    </div>
  );
}
