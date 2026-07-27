"use client";

import React, { useState } from "react";
import Link from "next/link";
import { WorkspaceProvider, useWorkspace } from "./components/WorkspaceProvider";
import { ExplorerTab } from "./components/ExplorerTab";
import { CleanerTab } from "./components/CleanerTab";
import { EDATab } from "./components/EDATab";
import { AutoMLTab } from "./components/AutoMLTab";
import { InsightsTab } from "./components/InsightsTab";
import { ChatSidebar } from "./components/ChatSidebar";
import { DashboardTab } from "./components/DashboardTab";
import ThemeSwitcher from "../components/ThemeSwitcher";
import { useAuth } from "@/lib/auth";
import Logo from "../components/Logo";
import ErrorState from "../components/ErrorState";
import { Table, Wand2, LayoutDashboard, Lightbulb, MessageSquare, FileText, Bot } from 'lucide-react';

function WorkspaceContent() {
  const { 
    activeTab, setActiveTab, 
    drawerOpen, setDrawerOpen, 
    profile, cleanProfile,
    sourceType, isSyncingSheets, syncSheets,
    apiError
  } = useWorkspace();
  const { user } = useAuth();
  
  const [uOpen, setUOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);

  const tabs = [
    { id: 'preview',   label: 'Preview',   icon: <Table size={14} /> },
    { id: 'cleaning',  label: 'Cleaning',  icon: <Wand2 size={14} /> },
    { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={14} /> },
    { id: 'insights',  label: 'Insights',  icon: <Lightbulb size={14} /> },
    { id: 'query',     label: 'AI Query',  icon: <MessageSquare size={14} /> },
    { id: 'eda',       label: 'Report',    icon: <FileText size={14} /> },
    { id: 'automl',    label: 'AutoML',    icon: <Bot size={14} /> },
  ];

  if (apiError) {
    return (
      <div className="flex flex-col h-screen" style={{ background: "var(--bg)" }}>
        <nav className="flex items-center px-5 h-[60px] border-b" style={{ background: "var(--nav)", borderColor: "var(--border)" }}>
           <Link href="/" className="no-underline"><Logo size={24} textSize={16} /></Link>
        </nav>
        <div className="flex-grow flex items-center justify-center">
           <ErrorState code={apiError.code} message={apiError.message} />
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden" style={{ background: "var(--bg)", color: "var(--txt)" }}>
      <div className="noise"></div>
      
      {/* NAV */}
      <nav id="topnav" className="sticky top-0 z-30 flex items-center shrink-0 px-3 h-[52px]" style={{ background: "var(--nav)", borderBottom: "1px solid var(--border)", backdropFilter: "blur(16px)" }}>
        <Link href="/" className="flex items-center gap-2.5 shrink-0 no-underline">
            <Logo size={24} textSize={16} />
        </Link>

        <div className="w-px h-5 mx-3 shrink-0" style={{ background: "var(--border)" }}></div>

        <div className="hidden md:flex items-center gap-[1px] flex-1 min-w-0 tab-strip">
          {tabs.map((tab) => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`ntab flex items-center gap-1.5 ${activeTab === tab.id ? 'na' : ''}`}>
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        <div className="flex-1"></div>

        {profile && (
          <div className="flex items-center gap-2 mr-3 font-mono text-[0.6rem] min-w-0" style={{ color: "var(--txt-m)" }}>
              <span className="font-bold shrink-0" style={{ color: "var(--txt)" }}>{profile.filename || 'dataset.csv'}</span>
              
              {cleanProfile && (
                  <span className="px-1.5 py-0.5 rounded text-[8px] font-black uppercase tracking-wider shrink-0" 
                        style={{ background: "rgba(16,185,129,.15)", border: "1px solid rgba(16,185,129,.3)", color: "#10b981" }}>
                      Cleaned
                  </span>
              )}

              {sourceType === 'sheets' && (
                  <button onClick={syncSheets} 
                          disabled={isSyncingSheets}
                          className="shrink-0 flex items-center gap-1 px-2 py-1 rounded text-[11px] font-bold whitespace-nowrap"
                          style={{ background: "var(--accent)", color: "white", border: "none", cursor: "pointer", lineHeight: 1 }}
                          title="Sync latest data from Google Sheets">
                      <svg className={`w-3 h-3 shrink-0 ${isSyncingSheets ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
                      </svg>
                      <span>{isSyncingSheets ? 'Syncing...' : 'Sync'}</span>
                  </button>
              )}

              <span className="shrink-0 hidden sm:inline" style={{ color: "var(--txt-f)" }}>·</span>
              <span className="hidden sm:inline">{((cleanProfile || profile).rows || 0).toLocaleString()} rows</span>
              <span className="hidden sm:inline" style={{ color: "var(--txt-f)" }}>·</span>
              <span className="hidden sm:inline">{((cleanProfile || profile).cols || 0)} cols</span>
          </div>
        )}


        <div className="relative ml-2 shrink-0 flex items-center gap-1">
          <ThemeSwitcher />
          {user ? (
            <>
              <button onClick={() => setUOpen(!uOpen)} className="flex items-center gap-2 pl-2 pr-2 py-1 rounded-lg border" style={{ borderColor: uOpen ? "var(--accent)" : "var(--border)", background: "transparent" }}>
                  {user.avatar ? (
                      <img src={user.avatar} className="w-6 h-6 rounded-full object-cover shrink-0" alt="" />
                  ) : (
                      <div className="w-6 h-6 rounded-full flex items-center justify-center text-[9px] font-black shrink-0" style={{ background: "var(--accent)", color: "#fff" }}>
                        {(user.name || 'U')[0].toUpperCase()}
                      </div>
                  )}
                  <span className="hidden sm:block font-bold text-[11px] max-w-[80px] truncate" style={{ color: "var(--txt)" }}>{user.name || user.email || 'User'}</span>
                  <svg className={`w-3 h-3 shrink-0 transition-transform ${uOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" style={{ color: "var(--txt-m)" }}><path d="M6 9l6 6 6-6"/></svg>
              </button>
              {uOpen && (
                  <div className="absolute right-0 top-full mt-2 w-48 rounded-xl shadow-2xl py-1 overflow-hidden" style={{ background: "var(--surface)", border: "1px solid var(--border)", zIndex: 9999 }}>
                      <div className="px-4 py-3 border-b" style={{ borderColor: "var(--border)" }}>
                          <p className="font-bold text-xs truncate" style={{ color: "var(--txt)" }}>{user.name || 'User'}</p>
                          <p className="text-[10px] truncate mt-0.5" style={{ color: "var(--txt-m)" }}>{user.email || ''}</p>
                      </div>
                      <a href="/dashboard" className="flex items-center gap-2.5 px-4 py-2.5 text-xs font-medium hover:opacity-80" style={{ color: "var(--txt-m)", textDecoration: "none" }}>My Account</a>
                      <a href="/api/logout" className="flex items-center gap-2.5 px-4 py-2.5 text-xs font-medium hover:opacity-80" style={{ color: "#ef4444", textDecoration: "none" }}>Sign Out</a>
                  </div>
              )}
            </>
          ) : (
              <a href="/login" className="px-3 py-1.5 rounded-lg text-[11px] font-bold border" style={{ borderColor: "var(--border)", color: "var(--txt-m)", textDecoration: "none" }}>Sign In</a>
          )}
        </div>
      </nav>

      {/* MOBILE TABS SUB-NAV */}
      <div className="md:hidden flex items-center overflow-x-auto no-scrollbar w-full px-2" style={{ background: "var(--nav)", borderBottom: "1px solid var(--border)", minHeight: "42px" }}>
          {tabs.map((tab) => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`shrink-0 flex items-center gap-1.5 px-3 py-2.5 text-[11px] font-bold border-b-2 transition-colors ${activeTab === tab.id ? 'border-[var(--accent)]' : 'border-transparent'}`} style={{ color: activeTab === tab.id ? "var(--txt)" : "var(--txt-m)" }}>
              {tab.icon}
              {tab.label}
            </button>
          ))}
      </div>

      <main id="main-content" className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden">
        <div style={{ display: activeTab === 'preview' ? 'block' : 'none', height: '100%' }}><ExplorerTab /></div>
        <div style={{ display: activeTab === 'cleaning' ? 'block' : 'none', height: '100%' }}><CleanerTab /></div>
        <div style={{ display: activeTab === 'eda' ? 'block' : 'none', height: '100%' }}><EDATab /></div>
        <div style={{ display: activeTab === 'automl' ? 'block' : 'none', height: '100%' }}><AutoMLTab /></div>
        <div style={{ display: activeTab === 'dashboard' ? 'block' : 'none', height: '100%' }}><DashboardTab /></div>
        <div style={{ display: activeTab === 'insights' ? 'block' : 'none', height: '100%' }}><InsightsTab /></div>
        <div style={{ display: activeTab === 'query' ? 'block' : 'none', height: '100%' }}><ChatSidebar /></div>
        
        {activeTab !== 'preview' && activeTab !== 'cleaning' && activeTab !== 'eda' && activeTab !== 'automl' && activeTab !== 'insights' && activeTab !== 'query' && activeTab !== 'dashboard' && (
          <div className="p-4">
            <h1 className="text-2xl font-bold">{activeTab} tab is under construction!</h1>
          </div>
        )}
      </main>

    </div>
  );
}

export default function WorkspacePage() {
  return (
    <WorkspaceProvider>
      <WorkspaceContent />
    </WorkspaceProvider>
  );
}
