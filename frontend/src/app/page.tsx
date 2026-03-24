"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { getProfiles, getBooks, deleteBook, Profile, Book } from "@/lib/api";
import UploadZone from "@/components/UploadZone";
import BookCard from "@/components/BookCard";

const HERO_GRADIENTS: Record<string, string> = {
  romance:      "from-rose-950 via-pink-950",
  fantasy:      "from-violet-950 via-purple-950",
  fiction:      "from-blue-950 via-slate-900",
  thriller:     "from-red-950 via-slate-950",
  mystery:      "from-slate-800 via-slate-900",
  biography:    "from-amber-950 via-yellow-950",
  "non-fiction":"from-teal-950 via-cyan-950",
  "self-help":  "from-emerald-950 via-green-950",
  classic:      "from-stone-800 via-stone-900",
  other:        "from-slate-800 via-slate-900",
};

export default function Home() {
  const router = useRouter();
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);
  const [showUpload, setShowUpload] = useState(false);
  const uploadRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getProfiles()
      .then(async (p) => {
        setProfiles(p);
        const defaultProfile = p.find((x) => x.is_default) ?? p[0];
        if (defaultProfile) {
          const bks = await getBooks(defaultProfile.id).catch(() => []);
          setBooks(bks);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleUploadComplete = (bookId: string, mode: "auto" | "manual") => {
    router.push(`/books/${bookId}?mode=${mode}`);
  };

  const handleDelete = async (bookId: string) => {
    await deleteBook(bookId);
    setBooks((prev) => prev.filter((b) => b.id !== bookId));
  };

  const featuredBook = books[0];
  const heroGradient = featuredBook?.genre
    ? HERO_GRADIENTS[featuredBook.genre.toLowerCase()] ?? HERO_GRADIENTS.other
    : null;

  return (
    <div className="min-h-screen bg-nf-bg">
      {/* ── Hero ──────────────────────────────────────────────────────────── */}
      <section className="relative min-h-[75vh] flex items-end overflow-hidden">
        {/* Background */}
        <div
          className={`absolute inset-0 bg-gradient-to-br ${heroGradient ?? "from-slate-900 via-slate-950"} to-nf-bg`}
        />
        {/* Vignette */}
        <div className="absolute inset-0"
          style={{ background: "linear-gradient(to bottom, rgba(0,0,0,0.3) 0%, transparent 40%, rgba(20,20,20,0.95) 85%, #141414 100%)" }}
        />

        {/* Hero content */}
        <div className="relative z-10 w-full px-8 md:px-14 pb-12 pt-32 animate-fade-up">
          {featuredBook && !showUpload ? (
            /* Featured book */
            <div className="max-w-xl">
              {featuredBook.genre && (
                <span className="mb-3 inline-block rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs capitalize text-white/80 backdrop-blur-sm">
                  {featuredBook.genre}
                </span>
              )}
              <h1 className="font-serif text-4xl md:text-5xl font-bold text-white leading-tight text-balance mb-3">
                {featuredBook.title}
              </h1>
              {featuredBook.author && (
                <p className="text-white/60 mb-5 text-sm">{featuredBook.author}</p>
              )}
              <div className="flex items-center gap-3 flex-wrap">
                <button
                  onClick={() => router.push(`/books/${featuredBook.id}`)}
                  className="flex items-center gap-2.5 rounded-lg bg-white px-6 py-3 text-sm font-bold text-black hover:bg-white/90 transition-colors"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M8 5v14l11-7z" />
                  </svg>
                  Open
                </button>
                <button
                  onClick={() => setShowUpload(true)}
                  className="flex items-center gap-2.5 rounded-lg bg-white/20 backdrop-blur-sm border border-white/20 px-6 py-3 text-sm font-semibold text-white hover:bg-white/30 transition-colors"
                >
                  <svg width="15" height="15" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                  </svg>
                  Upload new
                </button>
              </div>
            </div>
          ) : (
            /* Upload hero */
            <div className="max-w-2xl mx-auto text-center">
              <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-aged-gold">
                BookWiz
              </p>
              <h1 className="font-serif text-4xl md:text-5xl font-bold text-white text-balance mb-4">
                What are you reading?
              </h1>
              <p className="text-white/50 mb-10 text-base">
                Upload any book. Get characters, emotional scenes, and your personal scrapbook.
              </p>
              {loading ? (
                <div className="flex justify-center">
                  <div className="h-7 w-7 rounded-full border-2 border-aged-gold border-t-transparent animate-spin" />
                </div>
              ) : (
                <div ref={uploadRef}>
                  <UploadZone profiles={profiles} onUploadComplete={handleUploadComplete} />
                </div>
              )}
            </div>
          )}
        </div>
      </section>

      {/* Inline upload (when toggled from hero) */}
      {showUpload && featuredBook && (
        <section className="px-8 md:px-14 py-10 -mt-4 animate-fade-up">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-lg font-semibold text-white">Upload a new book</h2>
            <button onClick={() => setShowUpload(false)} className="text-white/40 hover:text-white transition-colors text-sm">
              Cancel
            </button>
          </div>
          <div className="max-w-xl">
            <UploadZone profiles={profiles} onUploadComplete={handleUploadComplete} />
          </div>
        </section>
      )}

      {/* ── My Books row ──────────────────────────────────────────────────── */}
      {books.length > 0 && (
        <section className="px-8 md:px-14 py-8 -mt-2 animate-fade-up">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">My Books</h2>
            <span className="text-xs text-white/40">{books.length} book{books.length !== 1 ? "s" : ""}</span>
          </div>
          <div className="flex gap-3 overflow-x-auto no-scrollbar pb-2">
            {books.map((book) => (
              <BookCard
                key={book.id}
                book={book}
                onClick={() => router.push(`/books/${book.id}`)}
                onDelete={handleDelete}
              />
            ))}
          </div>
        </section>
      )}

      {/* Bottom padding */}
      <div className="h-20" />
    </div>
  );
}
