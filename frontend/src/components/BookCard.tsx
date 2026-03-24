"use client";

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
}

export default function BookCard({ book, onClick }: BookCardProps) {
  const gradient = GENRE_GRADIENTS[book.genre?.toLowerCase() ?? ""] ?? GENRE_GRADIENTS.other;
  const badge = STATUS_BADGE[book.status] ?? { label: book.status, cls: "bg-white/10 text-white/50" };
  const isProcessing = ["processing", "free_text_requested"].includes(book.status);

  return (
    <div
      onClick={onClick}
      className="book-card-hover group relative flex-shrink-0 w-40 md:w-48 rounded-lg overflow-hidden"
      style={{ aspectRatio: "2/3", background: `linear-gradient(${gradient})` }}
    >
      {/* Subtle texture overlay */}
      <div className="absolute inset-0 opacity-20"
        style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg width='40' height='40' viewBox='0 0 40 40' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%23ffffff' fill-opacity='0.03'%3E%3Cpath d='M0 40L40 0H20L0 20M40 40V20L20 40'/%3E%3C/g%3E%3C/svg%3E\")" }}
      />

      {/* Processing spinner */}
      {isProcessing && (
        <div className="absolute top-3 right-3 h-4 w-4 rounded-full border-2 border-aged-gold border-t-transparent animate-spin" />
      )}

      {/* Genre badge top-left */}
      {book.genre && (
        <div className="absolute top-3 left-3">
          <span className="rounded-full bg-black/40 backdrop-blur-sm border border-white/10 px-2 py-0.5 text-[10px] capitalize text-white/70">
            {book.genre}
          </span>
        </div>
      )}

      {/* Bottom gradient + info */}
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

      {/* Hover overlay */}
      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center justify-center"
        style={{ background: "rgba(0,0,0,0.4)" }}
      >
        <div className="flex h-11 w-11 items-center justify-center rounded-full border-2 border-white bg-black/40 backdrop-blur-sm">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="white">
            <path d="M8 5v14l11-7z" />
          </svg>
        </div>
      </div>
    </div>
  );
}
