"use client";

import { useCallback, useState } from "react";
import { uploadBook, Profile } from "@/lib/api";

interface UploadZoneProps {
  profiles: Profile[];
  onUploadComplete: (bookId: string, mode: "auto" | "manual") => void;
}

export default function UploadZone({ profiles, onUploadComplete }: UploadZoneProps) {
  const [dragging, setDragging] = useState(false);
  const [mode, setMode] = useState<"manual" | "auto">("manual");
  const [profileId, setProfileId] = useState(
    profiles.find((p) => p.is_default)?.id ?? profiles[0]?.id ?? ""
  );
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const handleFile = useCallback(
    async (file: File) => {
      if (!file.name.match(/\.(pdf|epub)$/i)) {
        setError("Only PDF and EPUB files are supported.");
        return;
      }
      if (!profileId) {
        setError("Please select a profile first.");
        return;
      }
      setError("");
      setUploading(true);
      try {
        const result = await uploadBook(file, profileId, mode);
        onUploadComplete(result.book_id, mode);
      } catch (e: unknown) {
        const msg =
          (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          (e as Error)?.message ??
          "Upload failed. Make sure the backend is running.";
        setError(msg);
      } finally {
        setUploading(false);
      }
    },
    [profileId, mode, onUploadComplete]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  return (
    <div className="flex flex-col gap-5">
      {/* Profile selector */}
      {profiles.length > 1 && (
        <div className="flex items-center gap-3">
          <span className="text-xs text-white/40 uppercase tracking-wider">Profile</span>
          <div className="flex gap-2">
            {profiles.map((p) => (
              <button
                key={p.id}
                onClick={() => setProfileId(p.id)}
                className={`rounded-full px-4 py-1.5 text-xs font-medium transition-all ${
                  profileId === p.id
                    ? "bg-aged-gold text-black"
                    : "border border-white/15 text-white/50 hover:text-white hover:border-white/30"
                }`}
              >
                {p.profile_name}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Mode toggle */}
      <div className="flex items-center gap-4">
        <span className="text-xs text-white/40 uppercase tracking-wider">Mode</span>
        <div className="flex rounded-full border border-white/10 bg-white/5 p-0.5">
          {(["manual", "auto"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`rounded-full px-5 py-1.5 text-xs font-medium transition-all capitalize ${
                mode === m
                  ? "bg-white/15 text-white shadow-sm"
                  : "text-white/40 hover:text-white/70"
              }`}
            >
              {m === "manual" ? "Manual" : "Auto"}
            </button>
          ))}
        </div>
        <span className="text-xs text-white/30 hidden sm:block">
          {mode === "manual" ? "You pick the scenes" : "AI picks for you"}
        </span>
      </div>

      {/* Drop zone */}
      <label
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`relative flex h-44 cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed transition-all duration-300 ${
          dragging
            ? "border-aged-gold bg-aged-gold/8 scale-[1.01]"
            : "border-white/15 bg-white/4 hover:border-white/30 hover:bg-white/6"
        }`}
      >
        <input
          type="file"
          accept=".pdf,.epub"
          className="sr-only"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
          disabled={uploading}
        />

        {uploading ? (
          <div className="flex flex-col items-center gap-3">
            <div className="h-9 w-9 rounded-full border-2 border-aged-gold border-t-transparent animate-spin" />
            <p className="text-sm text-white/50">Uploading &amp; processing…</p>
          </div>
        ) : (
          <>
            {/* Upload icon */}
            <div className={`flex h-12 w-12 items-center justify-center rounded-full border border-white/15 bg-white/8 transition-transform ${dragging ? "scale-110" : ""}`}>
              <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8} className="text-white/60">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
              </svg>
            </div>
            <div className="text-center">
              <p className="text-sm font-medium text-white/75">
                Drop your book here
              </p>
              <p className="text-xs text-white/35 mt-1">PDF or EPUB · click to browse</p>
            </div>
          </>
        )}
      </label>

      {error && (
        <p className="rounded-lg border border-red-500/20 bg-red-900/15 px-4 py-2.5 text-sm text-red-400">
          {error}
        </p>
      )}
    </div>
  );
}
