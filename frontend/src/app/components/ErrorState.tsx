"use client";

import React from "react";
import Link from "next/link";
import { AlertTriangle, ShieldAlert, FileQuestion, ServerCrash, ArrowLeft } from "lucide-react";

interface ErrorStateProps {
  code?: number;
  title?: string;
  message?: string;
  reset?: () => void;
}

export default function ErrorState({ code = 500, title, message, reset }: ErrorStateProps) {
  let defaultTitle = "Something went wrong";
  let defaultMessage = "An unexpected error occurred while processing your request.";
  let Icon = ServerCrash;
  let colorVar = "var(--txt)";
  let bgVar = "rgba(255, 255, 255, 0.05)";
  let borderVar = "rgba(255, 255, 255, 0.1)";

  switch (code) {
    case 400:
      defaultTitle = "Bad Request";
      defaultMessage = "The request was invalid or could not be understood. Please check your data and try again.";
      Icon = AlertTriangle;
      colorVar = "#f59e0b"; // amber-500
      bgVar = "rgba(245, 158, 11, 0.1)";
      borderVar = "rgba(245, 158, 11, 0.2)";
      break;
    case 403:
      defaultTitle = "Access Denied";
      defaultMessage = "You do not have permission to view this resource. It might belong to another user.";
      Icon = ShieldAlert;
      colorVar = "#ef4444"; // red-500
      bgVar = "rgba(239, 68, 68, 0.1)";
      borderVar = "rgba(239, 68, 68, 0.2)";
      break;
    case 404:
      defaultTitle = "Not Found";
      defaultMessage = "We couldn't find the resource you're looking for. It may have been deleted or moved.";
      Icon = FileQuestion;
      colorVar = "var(--accent)";
      bgVar = "rgba(128, 128, 128, 0.1)";
      borderVar = "rgba(128, 128, 128, 0.2)";
      break;
    default:
      Icon = ServerCrash;
      break;
  }

  const finalTitle = title || defaultTitle;
  let finalMessage = message || defaultMessage;
  
  if (finalMessage === "upload_id required") {
    finalMessage = "Please launch a workspace or upload a dataset first.";
  }

  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center p-6 text-center w-full relative overflow-hidden" style={{ background: "var(--bg)" }}>
      {/* Background decorations */}
      <div className="absolute inset-0 pointer-events-none noise opacity-30"></div>
      <div className="absolute inset-0 pointer-events-none mesh opacity-20"></div>

      <div className="relative z-10 flex flex-col items-center max-w-lg w-full animate-in fade-in slide-in-from-bottom-4 duration-500">
        
        {/* Error Code Bubble */}
        <div 
          className="mb-8 w-24 h-24 rounded-3xl flex items-center justify-center transform -rotate-6 shadow-2xl" 
          style={{ background: bgVar, border: `1px solid ${borderVar}` }}
        >
          <div className="transform rotate-6 text-4xl font-black" style={{ color: colorVar }}>
            {code}
          </div>
        </div>

        {/* Text */}
        <h1 className="text-4xl md:text-5xl font-black tracking-tight mb-4" style={{ color: "var(--txt)" }}>
          {finalTitle}
        </h1>
        
        <p className="text-sm md:text-base leading-relaxed mb-8 px-4" style={{ color: "var(--txt-m)" }}>
          {finalMessage}
        </p>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row items-center gap-4">
          <Link href="/" className="btn-mag px-6 py-3 rounded-xl font-bold text-sm tracking-wide flex items-center gap-2 transition-all hover:scale-105" style={{ background: "var(--accent)", color: "#fff" }}>
            <ArrowLeft className="w-4 h-4" />
            Back to Dashboard
          </Link>
          
          {reset && (
            <button 
              onClick={reset}
              className="px-6 py-3 rounded-xl font-bold text-sm tracking-wide border transition-all hover:bg-opacity-10" 
              style={{ borderColor: "var(--border)", color: "var(--txt)", background: "transparent" }}
            >
              Try Again
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
