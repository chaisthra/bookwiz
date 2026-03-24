"use client";

import { useState } from "react";
import { Book } from "@/lib/api";

const GENRE_GRADIENTS: Record<string, string> = {
  romance:      "135deg, #5a1020, #2d0a1a, #141414",
  fantasy:      "135deg, #1a0845, #2a0e55, #141414",
  fiction:      "135deg, #0a1840, #101e50, #141414",
  thriller:     "135deg, #3a0505, #200303, #141414",
  mystery:      "135deg, #0e0e25, #14142e, #141414",
  biography:    "135deg, #3a2500, #281800, #141414",
  "non-fiction":"135deg, #002a2a, #001a1a, #141414",
  "self-help":  "135deg, #00251a, #001810, #141414",
  classic:      "135deg, #2a1800, #1a1000, #141414",
  other:        "135deg, #1a1a2a, #141420, #141414",
};

const STATUS_BADGE: Record<string, { label: string; cls: string }> = {
  processing:              { label: "Processing…", cls: "bg-aged-gold/20 text-aged-gold animate-pulse" },
  awaiting_scene_selection:{ label: "Choose scenes", cls: "bg-dusty-rose/20 text-dusty-rose" },
  free_text_requested:     { label: "Processing…",  cls: "bg-aged-gold/20 text-aged-gold animate-pulse" },
  complete:                { label: "Complete",      cls: "bg-muted-sage/20 text-muted-sage" },
  failed:                  { label: "Failed",        cls: "bg-red-900/30 text-red-400" },
};

interface BookCardProps {
  book: Book;
  onClick?: () => void;
  onDelete?: (bookId: string) => Promise<void>;
}

export default function BookCard({ book, onClick, onDelete }: BookCardProps) {
  const gradient = GENRE_GRADIENTS[book.genre?.toLowerCase() ?? ""] ?? GENRE_GRADIENTS.other;
  const badge = STATUS_BADGE[book.status] ?? { label: book.status, cls: "bg-white/10 text-white/50" };
  const isProcessing = ["processing", "free_text_requested"].includes(book.status);

  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting]     = useState(false);

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setConfirming(true);
  };

  const handleConfirm = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!onDelete) return;
    setDeleting(true);
    await onDelete(book.id);
    setDeleting(false);
    setConfirming(false);
  };

  const handleCancel = (e: React.MouseEvent) => {
    e.stopPropagation();
    setConfirming(false);
  };

  return (
    <div
      onClick={!confirming ? onClick : undefined}
      className="book-card-hover group relative flex-shrink-0 w-40 md:w-48 rounded-lg overflow-hidden cursor-pointer"
      style={{ aspectRatio: "2/3", background: `linear-gradient(${gradient})` }}
    >
      {/* Texture overlay */}
      <div className="absolute inset-0 opacity-20"
        style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg width='40' height='40' viewBox='0 0 40 40' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%23ffffff' fill-opacity='0.03'%3E%3Cpath d='M0 40L40 0H20L0 20M40 40V20L20 40'/%3E%3C/g%3E%3C/svg%3E\")" }}
      />

      {/* Processing spinner */}
      {isProcessing && !confirming && (
        <div className="absolute top-3 right-3 h-4 w-4 rounded-full border-2 border-aged-gold border-t-transparent animate-spin" />
      )}

      {/* Delete button — top right on hover */}
      {onDelete && !confirming && !isProcessing && (
        <button
          onClick={handleDeleteClick}
          className="absolute top-2 right-2 z-20 flex h-6 w-6 items-center justify-center rounded-full bg-black/70 border border-white/20 text-white/50 hover:text-red-400 hover:border-red-400/50 transition-all opacity-0 group-hover:opacity-100"
          title="Delete book"
        >
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}

      {/* Genre badge */}
      {book.genre && !confirming && (
        <div className="absolute top-3 left-3">
          <span className="rounded-full bg-black/40 backdrop-blur-sm border border-white/10 px-2 py-0.5 text-[10px] capitalize text-white/70">
            {book.genre}
          </span>
        </div>
      )}

      {/* Delete confirmation overlay */}
      {confirming && (
        <div
          className="absolute inset-0 z-30 flex flex-col items-center justify-center gap-3 px-4"
          style={{ background: "rgba(0,0,0,0.85)" }}
        >
          <p className="text-xs text-white/80 text-center leading-snug">
            Delete <span className="font-semibold text-white">{book.title}</span>?
          </p>
          <p className="text-[10px] text-white/40 text-center">This cannot be undone</p>
          <div className="flex gap-2 mt-1">
            <button
              onClick={handleConfirm}
              disabled={deleting}
              className="flex items-center gap-1 rounded-full bg-red-600 hover:bg-red-500 px-3 py-1 text-[11px] font-semibold text-white transition-colors disabled:opacity-50"
            >
              {deleting ? (
                <div className="h-3 w-3 rounded-full border border-white border-t-transparent animate-spin" />
              ) : "Delete"}
            </button>
            <button
              onClick={handleCancel}
              className="rounded-full border border-white/20 px-3 py-1 text-[11px] text-white/60 hover:text-white transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Bottom info */}
      <div className="absolute bottom-0 left-0 right-0 px-3 py-3"
        style={{ background: "linear-gradient(to top, rgba(0,0,0,0.95) 0%, rgba(0,0,0,0.6) 60%, transparent 100%)" }}
      >
        <p className="font-serif text-sm font-semibold text-white leading-tight line-clamp-2 mb-1.5">
          {book.title}
        </p>
        {book.author && (
          <p className="text-[10px] text-white/50 mb-1.5 truncate">{book.author}</p>
        )}
        <span className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-medium ${badge.cls}`}>
          {badge.label}
        </span>
      </div>

      {/* Hover open overlay */}
      {!confirming && (
        <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center justify-center pointer-events-none"
          style={{ background: "rgba(0,0,0,0.3)" }}
        >
          <div className="flex h-11 w-11 items-center justify-center rounded-full border-2 border-white bg-black/40 backdrop-blur-sm">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="white">
              <path d="M8 5v14l11-7z" />
            </svg>
          </div>
        </div>
      )}
    </div>
  );
}
