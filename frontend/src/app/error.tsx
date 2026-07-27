"use client";

import React, { useEffect } from "react";
import ErrorState from "./components/ErrorState";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Global Error Boundary caught:", error);
  }, [error]);

  return (
    <div className="flex-grow flex items-center justify-center min-h-screen">
      <ErrorState 
        code={500} 
        message={error.message || "A critical rendering error occurred."}
        reset={reset}
      />
    </div>
  );
}
