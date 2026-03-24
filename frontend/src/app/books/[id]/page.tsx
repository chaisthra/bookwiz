"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import {
  getBook, generateVisuals, regeneratePortrait, regenerateSceneImage,
  regenerateAllPortraits, regenerateAllSceneImages, BookDetail,
} from "@/lib/api";
import CharacterCard from "@/components/CharacterCard";
import SceneCard from "@/components/SceneCard";
import SceneSelector from "@/components/SceneSelector";

const GENRE_GRADIENTS: Record<string, string> = {
  romance:      "135deg, #5a1020 0%, #2d0a1a 40%, #141414 100%",
  fantasy:      "135deg, #1a0845 0%, #2a0e55 40%, #141414 100%",
  fiction:      "135deg, #0a1840 0%, #101e50 40%, #141414 100%",
  thriller:     "135deg, #3a0505 0%, #200303 40%, #141414 100%",
  mystery:      "135deg, #0e0e25 0%, #14142e 40%, #141414 100%",
  biography:    "135deg, #3a2500 0%, #281800 40%, #141414 100%",
  "non-fiction":"135deg, #002a2a 0%, #001a1a 40%, #141414 100%",
  "self-help":  "135deg, #00251a 0%, #001810 40%, #141414 100%",
  classic:      "135deg, #2a1800 0%, #1a1000 40%, #141414 100%",
  other:        "135deg, #1a1a2a 0%, #141420 40%, #141414 100%",
};

const STATUS_CONFIG: Record<string, { label: string; cls: string }> = {
  processing:               { label: "Analysing your book…",      cls: "text-aged-gold" },
  awaiting_scene_selection: { label: "Ready — choose your scenes", cls: "text-dusty-rose" },
  complete:                 { label: "Complete",                   cls: "text-muted-sage" },
  failed:                   { label: "Something went wrong",       cls: "text-red-400" },
  free_text_requested:      { label: "Processing your request…",   cls: "text-aged-gold" },
};

export default function BookPage() {
  const { id } = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const mode = searchParams.get("mode") ?? "manual";

  const [detail, setDetail] = useState<BookDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [generatingVisuals, setGeneratingVisuals] = useState(false);

  const fetchBook = useCallback(async () => {
    try {
      const data = await getBook(id);
      setDetail(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [id]);

  // SSE progress stream — replaces setInterval polling
  useEffect(() => {
    fetchBook();
    const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";
    const es = new EventSource(`${BACKEND}/books/${id}/progress`);
    let lastStatus = "";

    es.onmessage = (evt) => {
      try {
        const row = JSON.parse(evt.data) as {
          status?: string;
          visual_status?: string;
          current_step?: string;
          error?: string;
        };
        if (row.error) { es.close(); return; }

        // Live-update just the progress fields without a full fetch
        setDetail((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            book: {
              ...prev.book,
              status: row.status ?? prev.book.status,
              visual_status: row.visual_status ?? prev.book.visual_status,
              current_step: row.current_step ?? prev.book.current_step,
            },
          };
        });

        const key = `${row.status}|${row.visual_status}`;
        if (key !== lastStatus) {
          lastStatus = key;
          // Full re-fetch when status changes (picks up new characters/scenes)
          fetchBook();
        }
      } catch {
        // ignore malformed event
      }
    };

    es.onerror = () => { es.close(); };

    return () => es.close();
  }, [id, fetchBook]);

  const handleRegenPortrait = async (charId: string) => {
    try {
      const res = await regeneratePortrait(id, charId);
      return res.portrait_url;
    } catch { return null; }
  };

  const handleRegenSceneImage = async (sceneId: string) => {
    try {
      const res = await regenerateSceneImage(id, sceneId);
      return res.image_url;
    } catch { return null; }
  };

  const handleRegenAllPortraits = async () => {
    await regenerateAllPortraits(id);
  };

  const handleRegenAllSceneImages = async () => {
    await regenerateAllSceneImages(id);
  };

  const handleGenerateVisuals = async () => {
    setGeneratingVisuals(true);
    try {
      await generateVisuals(id);
      // SSE stream will pick up the visual_status change automatically
    } finally {
      setGeneratingVisuals(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-9 w-9 rounded-full border-2 border-aged-gold border-t-transparent animate-spin" />
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-white/40">Book not found.</p>
      </div>
    );
  }

  const { book, characters, scenes } = detail;
  const gradient  = GENRE_GRADIENTS[book.genre?.toLowerCase() ?? ""] ?? GENRE_GRADIENTS.other;
  const statusCfg = STATUS_CONFIG[book.status] ?? { label: book.status, cls: "text-white/50" };
  const isProcessing    = ["processing", "free_text_requested"].includes(book.status);
  const isGeneratingVis = ["generating_images", "generating_scrapbook"].includes(book.visual_status ?? "");
  const awaitingScenes  = book.status === "awaiting_scene_selection" && mode === "manual";
  const isComplete      = book.status === "complete";
  const hasVisuals      = book.visual_status === "visuals_complete";
  const canGenerateVis  = isComplete && !hasVisuals && !isGeneratingVis;

  const approvedScenes  = scenes.filter((s) => s.user_approved === true);
  const displayScenes   = approvedScenes.length > 0
    ? approvedScenes
    : scenes.filter((s) => s.user_approved !== false);

  return (
    <div className="min-h-screen bg-nf-bg">

      {/* ── Hero banner ────────────────────────────────────────────────── */}
      <section
        className="relative pt-28 pb-14 px-8 md:px-14 overflow-hidden"
        style={{ background: `linear-gradient(${gradient})` }}
      >
        <div className="absolute bottom-0 left-0 right-0 h-32"
          style={{ background: "linear-gradient(to bottom, transparent, #141414)" }}
        />
        <div className="relative z-10 max-w-3xl animate-fade-up">
          <button
            onClick={() => router.push("/")}
            className="mb-6 flex items-center gap-1.5 text-xs text-white/40 hover:text-white/80 transition-colors"
          >
            <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
            Back
          </button>

          <div className="flex items-center gap-3 mb-3 flex-wrap">
            {book.genre && (
              <span className="rounded-full border border-white/20 bg-white/10 backdrop-blur-sm px-3 py-0.5 text-xs capitalize text-white/80">
                {book.genre}
              </span>
            )}
            <span className={`text-sm font-medium ${statusCfg.cls} ${isProcessing || isGeneratingVis ? "animate-pulse" : ""}`}>
              {isGeneratingVis
                ? (book.current_step ?? "Generating visuals…")
                : statusCfg.label}
            </span>
          </div>

          <h1 className="font-serif text-3xl md:text-4xl font-bold text-white leading-tight mb-2 text-balance">
            {book.title}
          </h1>
          {book.author && (
            <p className="text-white/50 text-sm mb-5">{book.author}</p>
          )}

          {/* Processing spinner */}
          {(isProcessing || isGeneratingVis) && (
            <div className="flex items-center gap-3 mt-4">
              <div className="h-5 w-5 rounded-full border-2 border-aged-gold border-t-transparent animate-spin" />
              <span className="text-sm text-white/50">
                {book.current_step ?? "Extracting characters and scenes…"}
              </span>
            </div>
          )}

          {/* Action buttons */}
          {!isProcessing && !isGeneratingVis && (
            <div className="flex flex-wrap gap-3 mt-5">
              {hasVisuals && (
                <button
                  onClick={() => router.push(`/books/${id}/scrapbook`)}
                  className="flex items-center gap-2 rounded-full bg-aged-gold px-6 py-2.5 text-sm font-bold text-black hover:bg-aged-gold/90 transition-all"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 10h16M4 14h10" />
                  </svg>
                  View Scrapbook
                </button>
              )}
              {canGenerateVis && (
                <button
                  onClick={handleGenerateVisuals}
                  disabled={generatingVisuals}
                  className="flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-6 py-2.5 text-sm font-semibold text-white hover:bg-white/20 transition-all disabled:opacity-40"
                >
                  {generatingVisuals ? (
                    <div className="h-4 w-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
                  ) : (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                  )}
                  Generate Visuals
                </button>
              )}
            </div>
          )}
        </div>
      </section>

      <div className="px-8 md:px-14 pb-24 space-y-14">

        {/* ── Scene selector (manual mode) ────────────────────────────── */}
        {awaitingScenes && scenes.length > 0 && (
          <section className="animate-fade-up">
            <SceneSelector
              bookId={id}
              scenes={scenes}
              onComplete={() => { fetchBook(); }}
            />
          </section>
        )}

        {/* ── Characters ──────────────────────────────────────────────── */}
        {characters.length > 0 && (
          <section className="animate-fade-up">
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-serif text-xl font-semibold text-white">Characters</h2>
              {isComplete && (
                <button
                  onClick={handleRegenAllPortraits}
                  className="flex items-center gap-1.5 text-xs text-white/40 hover:text-white/70 transition-colors"
                  title="Regenerate all portraits"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Regenerate all portraits
                </button>
              )}
            </div>
            <div className="flex gap-4 overflow-x-auto no-scrollbar pb-2">
              {characters.map((c) => (
                <CharacterCard
                  key={c.id}
                  character={c}
                  onRegeneratePortrait={isComplete ? handleRegenPortrait : undefined}
                />
              ))}
            </div>
          </section>
        )}

        {/* ── Scenes ──────────────────────────────────────────────────── */}
        {!awaitingScenes && displayScenes.length > 0 && (
          <section className="animate-fade-up">
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-serif text-xl font-semibold text-white">
                {approvedScenes.length > 0 ? "Your Scenes" : "Scenes"}
              </h2>
              {isComplete && (
                <button
                  onClick={handleRegenAllSceneImages}
                  className="flex items-center gap-1.5 text-xs text-white/40 hover:text-white/70 transition-colors"
                  title="Regenerate all scene images"
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Regenerate all scene images
                </button>
              )}
            </div>
            <div className="flex gap-4 overflow-x-auto no-scrollbar pb-2">
              {displayScenes.map((s) => (
                <SceneCard
                  key={s.id}
                  scene={s}
                  onRegenerateImage={isComplete ? handleRegenSceneImage : undefined}
                />
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
