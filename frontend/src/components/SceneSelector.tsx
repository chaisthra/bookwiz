"use client";

import { useState } from "react";
import { Scene, selectScenes } from "@/lib/api";
import SceneCard from "./SceneCard";

interface SceneSelectorProps {
  bookId: string;
  scenes: Scene[];
  onComplete: () => void;
}

export default function SceneSelector({ bookId, scenes, onComplete }: SceneSelectorProps) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [freeText, setFreeText] = useState("");
  const [showFreeText, setShowFreeText] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");

  const toggle = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const handleConfirm = async () => {
    setSubmitError("");
    setSubmitting(true);
    try {
      const approved = [...selected];
      const rejected = scenes.map((s) => s.id).filter((id) => !selected.has(id));
      await selectScenes(bookId, approved, rejected, freeText || undefined);
      onComplete();
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        (e as Error)?.message ??
        "Failed to save your selection. Please try again.";
      setSubmitError(msg);
      setSubmitting(false);
    }
  };

  const handleFreeTextOnly = async () => {
    if (!freeText.trim()) return;
    setSubmitError("");
    setSubmitting(true);
    try {
      await selectScenes(bookId, [], [], freeText);
      onComplete();
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        (e as Error)?.message ??
        "Failed to save your request. Please try again.";
      setSubmitError(msg);
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-7">
      {/* Header */}
      <div>
        <h2 className="font-serif text-2xl font-bold text-white mb-1">
          Which scenes resonate with you?
        </h2>
        <p className="text-sm text-white/45">
          Select any that feel right — or describe what you want instead.
        </p>
      </div>

      {/* Scene cards — horizontal scroll */}
      <div className="flex gap-4 overflow-x-auto no-scrollbar pb-3">
        {scenes.map((scene) => (
          <SceneCard
            key={scene.id}
            scene={scene}
            selected={selected.has(scene.id)}
            onToggle={toggle}
            selectable
          />
        ))}
      </div>

      {/* Free-text escape hatch */}
      <div className="max-w-lg">
        <button
          onClick={() => setShowFreeText((v) => !v)}
          className="flex items-center gap-2 text-sm text-white/40 hover:text-white/70 transition-colors"
        >
          <svg
            width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
            className={`transition-transform ${showFreeText ? "rotate-45" : ""}`}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          {showFreeText ? "Hide" : "None of these — describe what you want"}
        </button>

        {showFreeText && (
          <div className="mt-3 space-y-3">
            <textarea
              value={freeText}
              onChange={(e) => setFreeText(e.target.value)}
              placeholder="e.g. 'The scene where she realises she loves him, and the final confrontation…'"
              rows={3}
              className="w-full rounded-xl border border-white/10 bg-nf-surface px-4 py-3 text-sm text-white placeholder-white/25 focus:border-aged-gold/40 focus:outline-none focus:ring-1 focus:ring-aged-gold/20 resize-none transition-colors"
            />
            <button
              onClick={handleFreeTextOnly}
              disabled={submitting || !freeText.trim()}
              className="rounded-full border border-white/15 bg-nf-elevated px-5 py-2 text-sm font-medium text-white transition-all hover:bg-white/10 disabled:opacity-40"
            >
              Use my description
            </button>
          </div>
        )}
      </div>

      {/* Error */}
      {submitError && (
        <p className="rounded-lg border border-red-500/20 bg-red-900/15 px-4 py-2.5 text-sm text-red-400 max-w-lg">
          {submitError}
        </p>
      )}

      {/* Confirm */}
      <div className="flex items-center gap-4">
        <button
          onClick={handleConfirm}
          disabled={submitting || selected.size === 0}
          className="flex items-center gap-2.5 rounded-full bg-aged-gold px-7 py-3 text-sm font-bold text-black transition-all hover:bg-aged-gold/90 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {submitting ? (
            <>
              <div className="h-4 w-4 rounded-full border-2 border-black border-t-transparent animate-spin" />
              Processing…
            </>
          ) : (
            <>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              Confirm {selected.size > 0 && `${selected.size} scene${selected.size !== 1 ? "s" : ""}`}
            </>
          )}
        </button>
        {selected.size > 0 && !submitting && (
          <span className="text-xs text-white/35">{selected.size} selected</span>
        )}
      </div>
    </div>
  );
}
