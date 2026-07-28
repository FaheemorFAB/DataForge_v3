"use client";

import React from "react";
import ErrorState from "./components/ErrorState";

export default function NotFound() {
  return (
    <div className="flex-grow flex items-center justify-center min-h-screen">
      <ErrorState 
        code={404} 
      />
    </div>
  );
}
