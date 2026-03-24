"use client";

import { useEffect, useState } from "react";

interface ToastProps {
  message: string;
  type?: "info" | "success" | "error";
  onDone: () => void;
}

export default function Toast({ message, type = "info", onDone }: ToastProps) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const hide  = setTimeout(() => setVisible(false), 2800);
    const clear = setTimeout(onDone, 3200);
    return () => { clearTimeout(hide); clearTimeout(clear); };
  }, [onDone]);

  const colours = {
    info:    "bg-white/10 border-white/20 text-white/80",
    success: "bg-muted-sage/20 border-muted-sage/40 text-muted-sage",
    error:   "bg-red-900/30 border-red-500/30 text-red-300",
  };

  return (
    <div
      className={`
        fixed bottom-6 left-1/2 -translate-x-1/2 z-50
        flex items-center gap-2.5 rounded-full border px-5 py-2.5
        text-sm font-medium backdrop-blur-md shadow-xl
        transition-all duration-400
        ${colours[type]}
        ${visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-3"}
      `}
    >
      {type === "info" && (
        <div className="h-3.5 w-3.5 rounded-full border-2 border-white/60 border-t-transparent animate-spin flex-shrink-0" />
      )}
      {type === "success" && (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} className="flex-shrink-0">
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      )}
      {type === "error" && (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} className="flex-shrink-0">
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      )}
      {message}
    </div>
  );
}
