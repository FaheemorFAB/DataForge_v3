"use client";

import React, { useState, useEffect, useRef } from "react";
import { useWorkspace } from "./WorkspaceProvider";
import { apiFetch } from "@/lib/api";
import { Check } from 'lucide-react';

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
  const [aiPermissionGranted, setAiPermissionGranted] = useState(false);

  const threadRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const quickActions = [
    "What are the top 5 anomalies?",
    "Show a correlation matrix",
    "Plot a histogram of sales",
    "Identify data quality issues",
    "Summarize the key trends",
  ];

  // Fetch initial sessions
  useEffect(() => {
    if (uploadId && aiPermissionGranted) {
      loadSessions();
    }
  }, [uploadId, aiPermissionGranted]);

  const loadSessions = async () => {
    try {
      const res = await apiFetch("/workspace/state");
      if (res.ok) {
        const st = await res.json();
        if (st.chat_sessions) setChatSessions(st.chat_sessions);
        if (st.chat_history) setMessages(st.chat_history);
      }
    } catch (e) {}
  };

  const createChatSession = async () => {
    try {
      const res = await apiFetch("/workspace/chat/session", { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        if (data.chat_sessions) setChatSessions(data.chat_sessions);
        setActiveSessionId(data.active_session);
        setMessages([]);
        if (window.innerWidth < 768) setChatSidebarOpen(false);
      }
    } catch (e) {}
  };

  const selectChatSession = async (id: string) => {
    if (window.innerWidth < 768) setChatSidebarOpen(false);
    if (id === activeSessionId) return;
    try {
      const res = await apiFetch(`/workspace/chat/session/select?id=${encodeURIComponent(id)}`, { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        setActiveSessionId(id);
        if (data.chat_sessions) setChatSessions(data.chat_sessions);
        setMessages(data.chat_history || []);
        scrollToBottom();
      }
    } catch (e) {}
  };

  const deleteChatSession = async (id: string) => {
    if (!confirm("Are you sure you want to delete this chat session?")) return;
    try {
      const res = await apiFetch(`/workspace/chat/session/${encodeURIComponent(id)}`, { method: "DELETE" });
      if (res.ok) {
        const data = await res.json();
        if (data.chat_sessions) setChatSessions(data.chat_sessions);
        setMessages(data.chat_history || []);
        setActiveSessionId(data.active_session);
      }
    } catch (e) {}
  };

  const startRenameSession = (id: string, currentName: string) => {
    setEditingSessionId(id);
    setEditingSessionName(currentName || "");
  };

  const renameChatSession = async (id: string) => {
    setEditingSessionId(null);
    try {
      const res = await apiFetch(`/workspace/chat/session/rename?id=${encodeURIComponent(id)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: editingSessionName }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.chat_sessions) setChatSessions(data.chat_sessions);
      }
    } catch (e) {}
  };

  const runQuery = async (q: string = query) => {
    if (!q.trim() || isAnalyzing) return;
    
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
          upload_id: uploadId
        }),
      });
      if (res.ok) {
        const data = await res.json();
        // Assume API returns updated chat history or latest message
        if (data.chat_sessions) {
          setChatSessions(data.chat_sessions);
        }
        if (data.active_session && !activeSessionId) {
           setActiveSessionId(data.active_session);
        }
        if (data.reply) {
           setMessages((prev) => [...prev, data.reply]);
        }
      } else {
        setMessages((prev) => [...prev, { role: "assistant", content: "Error: Failed to fetch response." }]);
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
      <div className="tab-panel space-y-5 px-4 py-4 md:px-6 md:py-6" style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div className="gc rounded-2xl p-6 text-center max-w-md space-y-4 shadow-2xl border" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
            <div className="w-12 h-12 rounded-full flex items-center justify-center mx-auto" style={{ background: "rgba(46,91,255,.08)", color: "var(--accent)" }}>
                <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.57-.598-3.75h-.152c-3.196 0-6.1-1.249-8.25-3.286zm0 3v1.5m0 3v.008H12v-.008z" />
                </svg>
            </div>
            <h3 className="text-lg font-black uppercase tracking-tight" style={{ color: "var(--txt)" }}>AI Data Sharing Consent</h3>
            <p className="text-xs leading-relaxed" style={{ color: "var(--txt-m)" }}>
                To support AI Chat, DataForge sends segments of your current dataset profile, columns, and query text to Google's Gemini models.
            </p>
            <div className="p-3 rounded-lg text-[11px] leading-relaxed text-left border space-y-1.5" style={{ background: "var(--bg)", borderColor: "var(--border)", color: "var(--txt-m)" }}>
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
                    <span>Data is processed securely and is not used to train models.</span>
                </div>
            </div>
            <p className="text-[10px]" style={{ color: "var(--txt-f)" }}>
                By clicking "Accept and Continue", you consent to sharing this session's metadata with the AI provider.
            </p>
            <div className="flex items-center gap-3 pt-2">
                <button onClick={() => setAiPermissionGranted(true)} className="bp flex-1 text-xs py-2 justify-center" style={{ cursor: "pointer" }}>Accept & Continue</button>
            </div>
        </div>
      </div>
    );
  }

  return (
    <div className="tab-panel h-full flex flex-col relative" style={{ padding: 0 }}>
      <div className="chat-container">
        
        {/* Mobile Sidebar Overlay */}
        <div className={`chat-sidebar-overlay ${chatSidebarOpen ? 'open' : ''}`} onClick={() => setChatSidebarOpen(false)}></div>

        {/* Sidebar */}
        <div className={`chat-sidebar ${chatSidebarOpen ? 'open' : 'collapsed-desktop'}`}>
          <button className="chat-sidebar-btn" onClick={createChatSession}>
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15"/></svg>
            New Chat
          </button>
          <p className="chat-sidebar-label">History</p>
          <div className="chat-sessions-list">
            {chatSessions.filter(s => true).map(s => (
              <div key={s.id} className={`chat-session-item ${activeSessionId === s.id ? 'active' : ''}`} onClick={() => selectChatSession(s.id)}>
                {editingSessionId === s.id ? (
                  <input
                    type="text"
                    value={editingSessionName}
                    onChange={e => setEditingSessionName(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter') renameChatSession(s.id); if (e.key === 'Escape') setEditingSessionId(null); }}
                    onBlur={() => renameChatSession(s.id)}
                    onClick={e => e.stopPropagation()}
                    className="chat-rename-input"
                    autoFocus
                  />
                ) : (
                  <div className="flex items-center w-full min-w-0 gap-1">
                    <svg className="w-3 h-3 flex-shrink-0 opacity-40" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.5 48.172 48.172 0 003.423-.38c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z"/></svg>
                    <span className="chat-session-title truncate">{s.name || 'Untitled Chat'}</span>
                    <div className="chat-session-actions" onClick={e => e.stopPropagation()}>
                        <button className="chat-action-btn" title="Rename" onClick={() => startRenameSession(s.id, s.name)}>
                            <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487z"/></svg>
                        </button>
                        <button className="chat-action-btn delete" title="Delete" onClick={() => deleteChatSession(s.id)}>
                            <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"/></svg>
                        </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
            {!chatSessions.length && (
              <div className="text-center py-8 opacity-40">
                  <svg className="w-8 h-8 mx-auto mb-2" fill="none" stroke="currentColor" strokeWidth="1.2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M8.625 9.75a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375m-13.5 3.01c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 01.865-.5 48.172 48.172 0 003.423-.38c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z"/></svg>
                  <p className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>No chats yet</p>
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
                          <rect x="3" y="3" width="18" height="18" rx="2"/>
                          <path d="M9 3v18"/>
                      </svg>
                  </button>
                  <div className="min-w-0">
                      <h3 className="font-black text-sm uppercase tracking-tight truncate" style={{ color: "var(--txt)" }}>
                          {chatSessions.find(s => s.id === activeSessionId)?.name || 'AI Chat'}
                      </h3>
                  </div>
              </div>
              <div className="flex items-center gap-1.5 flex-shrink-0">
                  <div className="w-1.5 h-1.5 rounded-full" style={{ background: "#22c55e", boxShadow: "0 0 5px #22c55e" }}></div>
                  <span className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>Gemini</span>
              </div>
          </div>

          {/* Thread */}
          <div id="chat-thread" ref={threadRef}>
            {!messages.length && (
              <div className="flex flex-col items-center justify-center py-12 gap-4 text-center">
                  <div className="w-14 h-14 rounded-2xl flex items-center justify-center text-2xl font-black italic"
                       style={{ background: "linear-gradient(135deg,var(--accent),rgba(99,102,241,.8))", color: "#fff", boxShadow: "0 8px 24px rgba(46,91,255,.3)" }}>AI</div>
                  <div>
                      <p className="font-black text-base uppercase tracking-tight" style={{ color: "var(--txt)" }}>DataForge Analyst</p>
                      <p className="text-xs mt-1 max-w-xs" style={{ color: "var(--txt-m)" }}>Ask me anything about your dataset — trends, stats, correlations, or custom queries.</p>
                  </div>
                  <div className="flex flex-wrap gap-2 justify-center max-w-sm">
                      {quickActions.map(action => (
                          <button key={action} onClick={() => runQuery(action)}
                                  className="chat-quick-chip" disabled={isAnalyzing}>{action}</button>
                      ))}
                  </div>
              </div>
            )}
            
            {messages.map((msg, i) => (
              <div key={i} className={`chat-msg-wrap ${msg.role}`}>
                {msg.role === 'assistant' ? (
                  <div>
                      <div className="chat-ai-header">
                          <div className="chat-ai-avatar">AI</div>
                          <span className="chat-ai-name">Analyst</span>
                      </div>
                      <div className="chat-bubble-ai">
                          <p>{msg.content}</p>
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
                        <span className="text-[10px] font-semibold ml-1" style={{ color: "var(--txt-m)" }}>Thinking…</span>
                    </div>
                </div>
            )}
          </div>

          {/* Input */}
          <div className="chat-input-wrap" style={{ margin: "1rem" }}>
              <textarea
                ref={textareaRef}
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); runQuery(); } }}
                placeholder="Ask anything about your data…"
                className="chat-textarea"
                rows={1}
                onInput={handleTextareaInput}
              />
              <button onClick={() => runQuery()} disabled={isAnalyzing || !query.trim()} className="chat-send-btn">
                  {!isAnalyzing ? (
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5"/></svg>
                  ) : (
                      <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
                  )}
              </button>
          </div>
          <p className="chat-input-hint text-center pb-2 text-[10px]" style={{ color: "var(--txt-m)" }}>Shift+Enter for new line · Enter to send</p>
        </div>
      </div>
    </div>
  );
}
